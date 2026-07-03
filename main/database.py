import json
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
except Exception:  # pragma: no cover - optional until requirements are installed
    MongoClient = None
    PyMongoError = Exception
    ServerSelectionTimeoutError = Exception

try:
    from bson import ObjectId
except Exception:  # pragma: no cover
    ObjectId = None

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DB_PATH = BASE_DIR / 'local_preview_db.json'

_client = None
_mongo_database = None
_mongo_available = None
_local_database = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialise(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialise(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialise(item) for key, item in value.items()}
    return value


def _load_local_db() -> Dict[str, List[Dict[str, Any]]]:
    if not LOCAL_DB_PATH.exists():
        return {}
    try:
        return json.loads(LOCAL_DB_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def _save_local_db(data: Dict[str, List[Dict[str, Any]]]) -> None:
    LOCAL_DB_PATH.write_text(json.dumps(_serialise(data), indent=2), encoding='utf-8')


def _match_regex(value: Any, pattern: str, options: str = '') -> bool:
    flags = re.IGNORECASE if 'i' in options else 0
    return re.search(pattern, str(value or ''), flags) is not None


def _matches_query(doc: Dict[str, Any], query: Optional[Dict[str, Any]]) -> bool:
    if not query:
        return True

    for key, expected in query.items():
        if key == '$or':
            return any(_matches_query(doc, sub_query) for sub_query in expected)

        current = doc.get(key)

        if isinstance(expected, dict) and '$regex' in expected:
            if not _match_regex(current, expected.get('$regex', ''), expected.get('$options', '')):
                return False
        elif current != expected:
            return False

    return True


class LocalCollection:
    def __init__(self, name: str):
        self.name = name
        global _local_database
        if _local_database is None:
            _local_database = _load_local_db()
        _local_database.setdefault(self.name, [])

    @property
    def _docs(self) -> List[Dict[str, Any]]:
        global _local_database
        _local_database.setdefault(self.name, [])
        return _local_database[self.name]

    def _save(self) -> None:
        _save_local_db(_local_database)

    def insert_one(self, document: Dict[str, Any]):
        doc = deepcopy(document)
        doc.setdefault('_id', uuid.uuid4().hex)
        self._docs.append(_serialise(doc))
        self._save()
        return type('InsertOneResult', (), {'inserted_id': doc['_id']})()

    def find(self, query: Optional[Dict[str, Any]] = None):
        return [deepcopy(doc) for doc in self._docs if _matches_query(doc, query)]

    def find_one(self, query: Optional[Dict[str, Any]] = None):
        for doc in self._docs:
            if _matches_query(doc, query):
                return deepcopy(doc)
        return None

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        modified = 0
        for index, doc in enumerate(self._docs):
            if _matches_query(doc, query):
                if '$set' in update:
                    doc.update(_serialise(update['$set']))
                self._docs[index] = doc
                modified = 1
                break
        self._save()
        return type('UpdateResult', (), {'modified_count': modified})()

    def delete_one(self, query: Dict[str, Any]):
        deleted = 0
        remaining = []
        for doc in self._docs:
            if deleted == 0 and _matches_query(doc, query):
                deleted = 1
                continue
            remaining.append(doc)
        global _local_database
        _local_database[self.name] = remaining
        self._save()
        return type('DeleteResult', (), {'deleted_count': deleted})()

    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        return len(self.find(query))


def _database_name_from_uri(uri: str) -> str:
    env_db = os.getenv('MONGODB_DB_NAME') or os.getenv('DB_NAME')
    if env_db:
        return env_db
    try:
        after_host = uri.split('.net/', 1)[1]
        db_name = after_host.split('?', 1)[0].strip('/')
        return db_name or 'ai_solution'
    except Exception:
        return 'ai_solution'


def _connect_mongo():
    global _client, _mongo_database, _mongo_available

    if _mongo_available is False:
        return None
    if _mongo_database is not None:
        return _mongo_database

    uri = os.getenv('MONGODB_URI', '').strip()
    if not uri or MongoClient is None:
        _mongo_available = False
        return None

    try:
        _client = MongoClient(uri, serverSelectionTimeoutMS=3500)
        _client.admin.command('ping')
        _mongo_database = _client[_database_name_from_uri(uri)]
        _mongo_available = True
        return _mongo_database
    except (PyMongoError, ServerSelectionTimeoutError, Exception):
        _mongo_available = False
        return None


def get_collection(name: str):
    database = _connect_mongo()
    if database is not None:
        return database[name]
    return LocalCollection(name)


def make_id(raw_id: str):
    if ObjectId is not None:
        try:
            if ObjectId.is_valid(str(raw_id)):
                return ObjectId(str(raw_id))
        except Exception:
            pass
    return str(raw_id)


def _format_datetime(value: Any) -> str:
    if not value:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%d %b %Y, %I:%M %p')
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed.strftime('%d %b %Y, %I:%M %p')
        except ValueError:
            return value
    return str(value)


def clean_doc(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not document:
        return None
    doc = dict(document)
    if '_id' in doc:
        doc['id'] = str(doc['_id'])
    doc['created_display'] = _format_datetime(doc.get('created_at'))
    doc['updated_display'] = _format_datetime(doc.get('updated_at'))
    return doc


def clean_docs(documents: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [clean_doc(doc) for doc in documents if clean_doc(doc) is not None]
