import base64
import csv
import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from functools import wraps
from typing import Dict, List, Tuple

from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .database import clean_doc, clean_docs, get_collection, make_id, utc_now


STATUS_OPTIONS = ['Received', 'Under Review', 'In Progress', 'Contacted', 'Completed', 'Closed']
FEEDBACK_STATUS_OPTIONS = ['Pending', 'Approved', 'Rejected']
IMAGE_LIMIT_MB = 2
MAX_IMAGES_PER_RECORD = 5
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


SERVICES = [
    {'icon': '🤖', 'title': 'AI Chatbot Development', 'description': 'Smart virtual assistants that answer customer questions, capture leads and improve response time.', 'features': ['FAQ automation', 'Lead capture', 'Website integration'], 'images': []},
    {'icon': '⚙️', 'title': 'Business Automation', 'description': 'Custom workflow automation that reduces repeated manual tasks and improves team productivity.', 'features': ['Process mapping', 'Task automation', 'Reporting'], 'images': []},
    {'icon': '📊', 'title': 'Data Analytics', 'description': 'Interactive dashboards and insights that help managers understand performance and make informed decisions.', 'features': ['Visual charts', 'Trend analysis', 'Decision support'], 'images': []},
    {'icon': '🚀', 'title': 'Digital Product Planning', 'description': 'Structured planning and interface design for businesses preparing new digital products.', 'features': ['MVP planning', 'User journey mapping', 'Feature roadmap'], 'images': []},
    {'icon': '🌐', 'title': 'Web Application Development', 'description': 'Secure, responsive and maintainable full-stack web systems for business operations.', 'features': ['Django', 'JavaScript', 'MongoDB Atlas'], 'images': []},
    {'icon': '💼', 'title': 'Digital Employee Experience', 'description': 'Self-service tools and knowledge systems that help employees work faster and smarter.', 'features': ['Employee portals', 'Support tools', 'Knowledge base'], 'images': []},
]

PROJECTS = [
    {'title': 'Healthcare Virtual Assistant', 'industry': 'Healthcare', 'description': 'A chatbot solution that helps patients find service information and appointment guidance.', 'technology': 'Django, JavaScript, MongoDB Atlas', 'result': 'Reduced repetitive front-desk queries.', 'details': 'The solution provides a simple chatbot interface, customer enquiry capture and admin-controlled FAQ training.', 'images': []},
    {'title': 'Retail Demand Dashboard', 'industry': 'Retail', 'description': 'An analytics dashboard that visualises sales enquiries and customer demand patterns.', 'technology': 'Python, MongoDB Atlas, JavaScript Charts', 'result': 'Improved decision-making for managers.', 'details': 'The dashboard shows enquiry trends, categories and service popularity to support business planning.', 'images': []},
    {'title': 'Education Support Portal', 'industry': 'Education', 'description': 'A responsive support platform for managing student enquiries and common questions.', 'technology': 'HTML, CSS, JavaScript, Django', 'result': 'Faster response to support requests.', 'details': 'The portal gives users a clear website interface and gives staff a dashboard for handling submitted enquiries.', 'images': []},
]

GALLERY_ITEMS = [
    {'title': 'AI Service Interface', 'category': 'Website Visual', 'description': 'A clean interface design for presenting AI services, service categories and enquiry actions.', 'details': 'This gallery item presents a business-facing interface layout with clear service cards, enquiry actions and visual hierarchy for professional visitors.', 'images': []},
    {'title': 'Admin Analytics Workspace', 'category': 'Dashboard Visual', 'description': 'A management workspace for reviewing enquiries, chatbot performance and feedback activity.', 'details': 'This gallery item highlights the professional admin workspace used for monitoring service demand, enquiry progress and content updates.', 'images': []},
    {'title': 'Chat Support Experience', 'category': 'Customer Support', 'description': 'A conversational support interface designed to guide website visitors toward the right service.', 'details': 'This gallery item shows how guided conversation can support visitor questions and direct users toward enquiry submission when required.', 'images': []},
]

EVENTS = [
    {'title': 'AI Innovation Workshop', 'date': '15 April 2026', 'location': 'Sunderland Business Hub', 'tag': 'Past Event', 'description': 'A client-focused workshop introducing AI tools for business efficiency.', 'details': 'This workshop introduced practical AI tools, chatbot walkthroughs, workflow automation examples and the benefits of digital transformation for business clients.', 'images': []},
    {'title': 'Digital Automation Showcase', 'date': '02 May 2026', 'location': 'AI-Solution Office', 'tag': 'Past Event', 'description': 'A showcase of workflow automation and chatbot integration for business teams.', 'details': 'The event showed how automation can reduce repeated work and how chatbot systems can support customer enquiries across business websites.', 'images': []},
    {'title': 'Future of AI Webinar', 'date': '22 June 2026', 'location': 'Online', 'tag': 'Upcoming', 'description': 'An online session about AI-powered software solutions for growing businesses.', 'details': 'This webinar covers AI adoption, digital product planning, chatbot design and secure digital transformation for small and medium businesses.', 'images': []},
]

ARTICLES = [
    {'title': 'How AI Chatbots Improve Customer Support', 'category': 'Chatbot', 'author': 'AI-Solution Team', 'date': '10 April 2026', 'summary': 'AI chatbots answer repeated questions instantly and guide visitors toward the right service.', 'content': 'AI chatbots improve customer support by answering repeated questions, collecting basic customer details and guiding users to the correct service page. They reduce waiting time and allow staff to focus on more complex customer needs.', 'images': []},
    {'title': 'Why Small Businesses Need Automation', 'category': 'Automation', 'author': 'AI-Solution Team', 'date': '26 April 2026', 'summary': 'Automation reduces repetitive work and helps teams focus on high-value business activities.', 'content': 'Automation helps small businesses reduce repeated manual tasks, improve accuracy and save time for employees and managers. It can be used for enquiry handling, reporting, reminders and internal workflows.', 'images': []},
    {'title': 'Using Data Dashboards for Better Decisions', 'category': 'Analytics', 'author': 'AI-Solution Team', 'date': '12 May 2026', 'summary': 'A clear dashboard turns raw data into useful insights for managers and decision-makers.', 'content': 'Dashboards organise data into visual reports so managers can understand trends, track performance and make better business decisions. They are especially useful for enquiry trends, customer demand and service performance.', 'images': []},
]

TESTIMONIALS = [
    {'name': 'Daniel Carter', 'role': 'Operations Manager', 'rating': '5', 'quote': 'AI-Solution helped us understand how automation could improve our customer workflow.', 'status': 'Approved', 'images': []},
    {'name': 'Sophia Lee', 'role': 'Product Lead', 'rating': '5', 'quote': 'The platform was professional, fast and easy for non-technical users to understand.', 'status': 'Approved', 'images': []},
    {'name': 'Marcus Green', 'role': 'Business Consultant', 'rating': '4', 'quote': 'Clean interface, useful chatbot and a practical admin dashboard for managing enquiries.', 'status': 'Approved', 'images': []},
]

CHATBOT_FAQS = [
    {'question': 'What services do you provide?', 'intent': 'services', 'keywords': 'service, services, offer, provide, chatbot, automation, analytics, software, ai, development', 'answer': 'AI-Solution provides AI chatbot development, business automation, data analytics, digital product planning, web application development and digital employee experience solutions.', 'priority': '10', 'enabled': 'yes'},
    {'question': 'How much does a project cost?', 'intent': 'pricing', 'keywords': 'price, pricing, cost, budget, fee, charge, package, quote', 'answer': 'Project cost depends on the required features and complexity. Please submit your details through the Contact page and our team will prepare a suitable proposal.', 'priority': '8', 'enabled': 'yes'},
    {'question': 'How can I contact AI-Solution?', 'intent': 'contact', 'keywords': 'contact, email, phone, enquiry, inquiry, reach, message, call, quote', 'answer': 'You can contact AI-Solution by filling out the Contact page with your name, email, phone number, company name, country, job title and project details.', 'priority': '9', 'enabled': 'yes'},
    {'question': 'How can I track my enquiry?', 'intent': 'tracking', 'keywords': 'track, tracking, enquiry, inquiry, status, reference, id, progress', 'answer': 'Use the Track Enquiry page and enter your tracking ID or email address to view the latest enquiry status.', 'priority': '9', 'enabled': 'yes'},
    {'question': 'What technologies are used?', 'intent': 'technology', 'keywords': 'technology, technologies, stack, python, django, mongodb, atlas, html, css, javascript', 'answer': 'The platform uses Python Django for the backend, MongoDB Atlas for data storage, and HTML, CSS and JavaScript for the frontend.', 'priority': '9', 'enabled': 'yes'},
]

CONTENT_MODULES = {
    'services': {'title': 'Services Management', 'singular': 'Service', 'collection': 'services', 'defaults': SERVICES, 'supports_images': True, 'list_fields': [('icon', 'Icon'), ('title', 'Title'), ('description', 'Description')], 'fields': [
        {'name': 'icon', 'label': 'Icon', 'type': 'text', 'required': True, 'placeholder': 'Example: 🤖'},
        {'name': 'title', 'label': 'Service Title', 'type': 'text', 'required': True, 'placeholder': 'Example: AI Chatbot Development'},
        {'name': 'description', 'label': 'Description', 'type': 'textarea', 'required': True, 'placeholder': 'Write service description'},
        {'name': 'features', 'label': 'Features', 'type': 'textarea', 'required': True, 'placeholder': 'Write features separated by commas'},
    ]},
    'projects': {'title': 'Portfolio Management', 'singular': 'Project', 'collection': 'projects', 'defaults': PROJECTS, 'supports_images': True, 'list_fields': [('industry', 'Industry'), ('title', 'Title'), ('technology', 'Technology')], 'fields': [
        {'name': 'title', 'label': 'Project Title', 'type': 'text', 'required': True, 'placeholder': 'Example: Healthcare Virtual Assistant'},
        {'name': 'industry', 'label': 'Industry', 'type': 'text', 'required': True, 'placeholder': 'Example: Healthcare'},
        {'name': 'description', 'label': 'Description', 'type': 'textarea', 'required': True, 'placeholder': 'Short project description'},
        {'name': 'technology', 'label': 'Technology', 'type': 'text', 'required': True, 'placeholder': 'Example: Django, JavaScript, MongoDB'},
        {'name': 'result', 'label': 'Result', 'type': 'textarea', 'required': True, 'placeholder': 'Write project result'},
        {'name': 'details', 'label': 'Full Project Details', 'type': 'textarea', 'required': True, 'placeholder': 'Write full project details for the detail page'},
    ]},
    'gallery': {'title': 'Gallery Management', 'singular': 'Gallery Item', 'collection': 'gallery_items', 'defaults': GALLERY_ITEMS, 'supports_images': True, 'list_fields': [('category', 'Category'), ('title', 'Title'), ('description', 'Description')], 'fields': [
        {'name': 'title', 'label': 'Gallery Title', 'type': 'text', 'required': True, 'placeholder': 'Example: AI Service Interface'},
        {'name': 'category', 'label': 'Category', 'type': 'text', 'required': True, 'placeholder': 'Example: Dashboard Visual'},
        {'name': 'description', 'label': 'Short Description', 'type': 'textarea', 'required': True, 'placeholder': 'Short card description'},
        {'name': 'details', 'label': 'Full Details', 'type': 'textarea', 'required': True, 'placeholder': 'Write full details for the detail page'},
    ]},
    'events': {'title': 'Events Management', 'singular': 'Event', 'collection': 'events', 'defaults': EVENTS, 'supports_images': True, 'list_fields': [('tag', 'Type'), ('title', 'Title'), ('date', 'Date')], 'fields': [
        {'name': 'title', 'label': 'Event Title', 'type': 'text', 'required': True, 'placeholder': 'Example: AI Innovation Workshop'},
        {'name': 'date', 'label': 'Date', 'type': 'text', 'required': True, 'placeholder': 'Example: 15 April 2026'},
        {'name': 'location', 'label': 'Location', 'type': 'text', 'required': False, 'placeholder': 'Example: Online or Sunderland Business Hub'},
        {'name': 'tag', 'label': 'Type/Tag', 'type': 'text', 'required': True, 'placeholder': 'Example: Past Event or Upcoming'},
        {'name': 'description', 'label': 'Short Description', 'type': 'textarea', 'required': True, 'placeholder': 'Short card description'},
        {'name': 'details', 'label': 'Full Event Details', 'type': 'textarea', 'required': True, 'placeholder': 'Write full event details for the detail page'},
    ]},
    'articles': {'title': 'Articles Management', 'singular': 'Article', 'collection': 'articles', 'defaults': ARTICLES, 'supports_images': True, 'list_fields': [('category', 'Category'), ('title', 'Title'), ('date', 'Date')], 'fields': [
        {'name': 'title', 'label': 'Article Title', 'type': 'text', 'required': True, 'placeholder': 'Example: How AI Chatbots Improve Customer Support'},
        {'name': 'category', 'label': 'Category', 'type': 'text', 'required': True, 'placeholder': 'Example: Chatbot'},
        {'name': 'author', 'label': 'Author', 'type': 'text', 'required': False, 'placeholder': 'Example: AI-Solution Team'},
        {'name': 'date', 'label': 'Date', 'type': 'text', 'required': True, 'placeholder': 'Example: 10 April 2026'},
        {'name': 'summary', 'label': 'Summary', 'type': 'textarea', 'required': True, 'placeholder': 'Short article summary'},
        {'name': 'content', 'label': 'Article Content', 'type': 'textarea', 'required': True, 'placeholder': 'Full article content'},
    ]},
    'testimonials': {'title': 'Feedback & Testimonials', 'singular': 'Feedback Record', 'collection': 'testimonials', 'defaults': TESTIMONIALS, 'supports_images': True, 'list_fields': [('status', 'Status'), ('name', 'Client'), ('rating', 'Rating')], 'fields': [
        {'name': 'name', 'label': 'Client Name', 'type': 'text', 'required': True, 'placeholder': 'Example: Daniel Carter'},
        {'name': 'role', 'label': 'Role/Company', 'type': 'text', 'required': True, 'placeholder': 'Example: Operations Manager'},
        {'name': 'rating', 'label': 'Rating', 'type': 'select', 'required': True, 'choices': ['5', '4', '3', '2', '1'], 'placeholder': 'Choose rating'},
        {'name': 'quote', 'label': 'Feedback Message', 'type': 'textarea', 'required': True, 'placeholder': 'Write feedback'},
        {'name': 'status', 'label': 'Approval Status', 'type': 'select', 'required': True, 'choices': FEEDBACK_STATUS_OPTIONS, 'placeholder': 'Choose status'},
    ]},
    'chatbot': {'title': 'Chatbot Training', 'singular': 'Chatbot Training Record', 'collection': 'chatbot_faqs', 'defaults': CHATBOT_FAQS, 'supports_images': False, 'list_fields': [('intent', 'Intent'), ('question', 'Question'), ('priority', 'Priority')], 'fields': [
        {'name': 'question', 'label': 'Training Question', 'type': 'text', 'required': True, 'placeholder': 'Example: What services do you provide?'},
        {'name': 'intent', 'label': 'Intent / Category', 'type': 'text', 'required': True, 'placeholder': 'Example: services, pricing, contact'},
        {'name': 'keywords', 'label': 'Training Keywords', 'type': 'textarea', 'required': True, 'placeholder': 'Write keywords separated by commas'},
        {'name': 'answer', 'label': 'Bot Answer', 'type': 'textarea', 'required': True, 'placeholder': 'Write chatbot answer'},
        {'name': 'priority', 'label': 'Priority', 'type': 'text', 'required': True, 'placeholder': 'Example: 10'},
        {'name': 'enabled', 'label': 'Enabled', 'type': 'select', 'required': True, 'choices': ['yes', 'no'], 'placeholder': 'yes or no'},
    ]},
}

CODE_TRAINED_INTENTS = [
    {'intent': 'greeting', 'patterns': ['hello', 'hi', 'hey', 'good morning', 'good afternoon'], 'keywords': ['hello', 'hi', 'hey', 'start'], 'answer': 'Hello! I am the AI-Solution assistant. I can help with services, pricing, portfolio, gallery, events, articles, enquiry tracking and contact support.'},
    {'intent': 'services', 'patterns': ['what services do you provide', 'what do you offer', 'do you make chatbots'], 'keywords': ['service', 'services', 'offer', 'provide', 'chatbot', 'automation', 'analytics', 'development'], 'answer': 'AI-Solution provides chatbot development, automation systems, data analytics, digital product planning, web application development and digital employee experience solutions.'},
    {'intent': 'portfolio', 'patterns': ['show previous projects', 'past work', 'portfolio'], 'keywords': ['portfolio', 'project', 'projects', 'case', 'work', 'previous', 'solution'], 'answer': 'You can view previous industry solutions on the Portfolio page. It includes project descriptions, technologies and outcomes.'},
    {'intent': 'gallery', 'patterns': ['gallery', 'project gallery', 'visuals'], 'keywords': ['gallery', 'image', 'images', 'visual', 'media', 'interface'], 'answer': 'The Gallery page presents project visuals, service interface examples and platform media.'},
    {'intent': 'events', 'patterns': ['events', 'upcoming events', 'workshop'], 'keywords': ['event', 'events', 'workshop', 'webinar', 'upcoming', 'past'], 'answer': 'The Events page shows workshops, webinars and business activities related to AI solutions, automation and software innovation.'},
    {'intent': 'articles', 'patterns': ['articles', 'blog', 'news'], 'keywords': ['article', 'articles', 'blog', 'news', 'post', 'read'], 'answer': 'The Articles page contains company news and AI-related insight articles.'},
    {'intent': 'pricing', 'patterns': ['how much does it cost', 'pricing', 'budget'], 'keywords': ['price', 'pricing', 'cost', 'budget', 'fee', 'charge', 'package', 'quote'], 'answer': 'Project pricing depends on the features and complexity. Submit your enquiry from the Contact page and the team will prepare a suitable proposal.'},
    {'intent': 'tracking', 'patterns': ['track enquiry', 'check enquiry status', 'tracking id'], 'keywords': ['track', 'tracking', 'status', 'enquiry', 'inquiry', 'id', 'reference', 'progress'], 'answer': 'You can use the Track Enquiry page and enter your tracking ID or email address to view the current status.'},
    {'intent': 'contact', 'patterns': ['how can I contact you', 'contact details'], 'keywords': ['contact', 'email', 'phone', 'enquiry', 'inquiry', 'message', 'call', 'reach'], 'answer': 'Please use the Contact page to submit your name, email, phone, company, country, job title and project details.'},
    {'intent': 'technology', 'patterns': ['what technology is used', 'tech stack'], 'keywords': ['python', 'django', 'mongodb', 'atlas', 'html', 'css', 'javascript', 'technology', 'stack'], 'answer': 'The platform uses Python Django, MongoDB Atlas, HTML, CSS and JavaScript.'},
    {'intent': 'admin', 'patterns': ['what can admin do', 'admin dashboard'], 'keywords': ['admin', 'dashboard', 'manage', 'train', 'faq', 'login'], 'answer': 'Admin can manage enquiries, services, portfolio, gallery, events, articles, feedback approvals and chatbot training records.'},
    {'intent': 'bye', 'patterns': ['bye', 'goodbye', 'thanks'], 'keywords': ['bye', 'goodbye', 'thanks', 'thank'], 'answer': 'You are welcome. Submit the Contact form if you want the AI-Solution team to follow up.'},
]


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_logged_in'):
            messages.warning(request, 'Please login to access the admin dashboard.')
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _module_or_404(module_slug: str) -> Dict:
    module = CONTENT_MODULES.get(module_slug)
    if not module:
        raise Http404('Admin module not found')
    return module


def _settings_collection():
    return get_collection('app_settings')


def _seed_collection(module_slug: str) -> None:
    module = _module_or_404(module_slug)
    settings_key = f'seeded_{module_slug}'
    settings = _settings_collection().find_one({'key': settings_key})
    if settings:
        return
    collection = get_collection(module['collection'])
    if collection.count_documents({}) == 0:
        for item in module['defaults']:
            payload = dict(item)
            payload['created_at'] = utc_now()
            payload['updated_at'] = utc_now()
            collection.insert_one(payload)
    _settings_collection().insert_one({'key': settings_key, 'value': True, 'created_at': utc_now()})


def _get_content(module_slug: str) -> List[Dict]:
    _seed_collection(module_slug)
    module = _module_or_404(module_slug)
    docs = clean_docs(get_collection(module['collection']).find({}))
    docs.sort(key=lambda item: str(item.get('created_at', '')), reverse=False)
    return docs


def _approved_testimonials() -> List[Dict]:
    return [item for item in _get_content('testimonials') if str(item.get('status', 'Approved')).lower() == 'approved']


def _get_content_item(module_slug: str, item_id: str) -> Dict:
    module = _module_or_404(module_slug)
    item = clean_doc(get_collection(module['collection']).find_one({'_id': make_id(item_id)}))
    if not item:
        raise Http404('Item not found')
    return item


def _uploaded_images(files) -> Tuple[List[Dict], List[str]]:
    images = []
    errors = []
    for image_file in files:
        if not image_file:
            continue
        if image_file.content_type not in ALLOWED_IMAGE_TYPES:
            errors.append(f'{image_file.name} is not a supported image type.')
            continue
        if image_file.size > IMAGE_LIMIT_MB * 1024 * 1024:
            errors.append(f'{image_file.name} is larger than {IMAGE_LIMIT_MB} MB.')
            continue
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
        images.append({'name': image_file.name, 'content_type': image_file.content_type, 'data_url': f'data:{image_file.content_type};base64,{encoded}'})
    return images, errors


def _existing_images_from_post(post_data) -> List[Dict]:
    if post_data.get('clear_images') == 'on':
        return []
    raw = post_data.get('existing_images_json', '[]')
    try:
        images = json.loads(raw)
        if isinstance(images, list):
            return images
    except json.JSONDecodeError:
        pass
    return []


def _prepare_form_rows(module: Dict, data: Dict = None) -> List[Dict]:
    data = data or {}
    rows = []
    for field in module['fields']:
        value = data.get(field['name'], '')
        if isinstance(value, list):
            value = ', '.join(str(item) for item in value)
        row = dict(field)
        row['value'] = value
        rows.append(row)
    return rows


def _content_payload(module: Dict, post_data, files=None, existing_item=None) -> Tuple[Dict, List[str]]:
    payload = {}
    errors = []
    existing_item = existing_item or {}
    for field in module['fields']:
        name = field['name']
        value = post_data.get(name, '').strip()
        if field.get('required') and not value:
            errors.append(field['label'])
        if name == 'features':
            payload[name] = [item.strip() for item in value.split(',') if item.strip()]
        else:
            payload[name] = value
    if 'enabled' in payload:
        payload['enabled'] = payload['enabled'].lower() if payload['enabled'] else 'yes'
    if 'status' in payload and module.get('collection') == 'testimonials':
        if payload['status'] not in FEEDBACK_STATUS_OPTIONS:
            payload['status'] = 'Pending'
    if module.get('supports_images'):
        existing_images = _existing_images_from_post(post_data) if existing_item else []
        new_images, image_errors = _uploaded_images(files.getlist('images') if files else [])
        errors.extend(image_errors)
        payload['images'] = existing_images + new_images
        if len(payload['images']) > MAX_IMAGES_PER_RECORD:
            errors.append(f'Maximum {MAX_IMAGES_PER_RECORD} images are allowed per record.')
    return payload, errors


def _table_rows(module: Dict, docs: List[Dict]) -> List[Dict]:
    rows = []
    for doc in docs:
        values = []
        for key, _label in module['list_fields']:
            value = doc.get(key, '')
            if isinstance(value, list):
                value = ', '.join(str(item) for item in value)
            values.append(value)
        rows.append({'id': doc.get('id'), 'values': values, 'created_display': doc.get('created_display'), 'raw': doc})
    return rows


def _next_sequence_number() -> int:
    return get_collection('inquiries').count_documents({}) + 1


def _generate_tracking_id() -> str:
    year = datetime.utcnow().strftime('%Y')
    return f'AIS-{year}-{_next_sequence_number():04d}'


def _inquiry_payload(post_data) -> Tuple[Dict[str, str], List[str]]:
    fields = {
        'tracking_id': post_data.get('tracking_id', '').strip(),
        'name': post_data.get('name', '').strip(),
        'email': post_data.get('email', '').strip(),
        'phone': post_data.get('phone', '').strip(),
        'company_name': post_data.get('company_name', '').strip(),
        'country': post_data.get('country', '').strip(),
        'job_title': post_data.get('job_title', '').strip(),
        'job_details': post_data.get('job_details', '').strip(),
        'service_interest': post_data.get('service_interest', '').strip(),
        'budget_range': post_data.get('budget_range', '').strip(),
        'preferred_contact_time': post_data.get('preferred_contact_time', '').strip(),
        'admin_notes': post_data.get('admin_notes', '').strip(),
        'status': post_data.get('status', 'Received').strip() or 'Received',
    }
    required = ['name', 'email', 'phone', 'company_name', 'country', 'job_title', 'job_details']
    errors = [field.replace('_', ' ').title() for field in required if not fields[field]]
    if fields['status'] not in STATUS_OPTIONS:
        fields['status'] = 'Received'
    if not fields['tracking_id']:
        fields['tracking_id'] = _generate_tracking_id()
    return fields, errors


def _feedback_payload(post_data) -> Tuple[Dict[str, str], List[str]]:
    payload = {
        'name': post_data.get('name', '').strip(),
        'email': post_data.get('email', '').strip(),
        'role': post_data.get('role', '').strip(),
        'rating': post_data.get('rating', '').strip(),
        'quote': post_data.get('quote', '').strip(),
        'status': 'Pending',
        'images': [],
    }
    required = ['name', 'email', 'role', 'rating', 'quote']
    errors = [field.replace('_', ' ').title() for field in required if not payload[field]]
    if payload['rating'] not in ['5', '4', '3', '2', '1']:
        payload['rating'] = '5'
    return payload, errors


def _count_by(docs: List[Dict], field: str, options: List[str] = None) -> List[Dict]:
    counts = {}
    for doc in docs:
        key = str(doc.get(field) or 'Not Set')
        counts[key] = counts.get(key, 0) + 1
    if options:
        for option in options:
            counts.setdefault(option, 0)
    total = max(sum(counts.values()), 1)
    return [{'label': key, 'count': value, 'percent': int((value / total) * 100)} for key, value in counts.items()]


def home(request):
    inquiries = get_collection('inquiries')
    context = {
        'services': _get_content('services')[:6],
        'projects': _get_content('projects')[:3],
        'gallery_items': _get_content('gallery')[:3],
        'events': _get_content('events')[:3],
        'articles': _get_content('articles')[:3],
        'testimonials': _approved_testimonials()[:3],
        'total_inquiries': inquiries.count_documents({}),
    }
    return render(request, 'home.html', context)


def services(request):
    return render(request, 'services.html', {'services': _get_content('services')})


def portfolio(request):
    return render(request, 'portfolio.html', {'projects': _get_content('projects')})


def project_detail(request, item_id):
    return render(request, 'project_detail.html', {'project': _get_content_item('projects', item_id)})


def gallery(request):
    return render(request, 'gallery.html', {'gallery_items': _get_content('gallery')})


def gallery_detail(request, item_id):
    return render(request, 'gallery_detail.html', {'item': _get_content_item('gallery', item_id)})


def events(request):
    return render(request, 'events.html', {'events': _get_content('events')})


def event_detail(request, item_id):
    return render(request, 'event_detail.html', {'event': _get_content_item('events', item_id)})


def articles(request):
    query = request.GET.get('q', '').strip().lower()
    all_articles = _get_content('articles')
    filtered = all_articles
    if query:
        filtered = [article for article in all_articles if query in article.get('title', '').lower() or query in article.get('category', '').lower() or query in article.get('summary', '').lower()]
    return render(request, 'articles.html', {'articles': filtered, 'query': query})


def article_detail(request, item_id):
    return render(request, 'article_detail.html', {'article': _get_content_item('articles', item_id)})


def contact(request):
    if request.method == 'POST':
        payload, errors = _inquiry_payload(request.POST)
        if errors:
            messages.error(request, 'Please complete these required fields: ' + ', '.join(errors))
            return render(request, 'contact.html', {'form_data': payload, 'services': _get_content('services')})
        payload['created_at'] = utc_now()
        payload['updated_at'] = utc_now()
        get_collection('inquiries').insert_one(payload)
        messages.success(request, f'Thank you for contacting AI-Solution. Your tracking ID is {payload["tracking_id"]}.')
        return render(request, 'contact.html', {'services': _get_content('services'), 'submitted_tracking_id': payload['tracking_id']})
    return render(request, 'contact.html', {'services': _get_content('services')})


def track_enquiry(request):
    result = None
    searched = False
    query_value = ''
    email = ''
    if request.method == 'POST':
        searched = True
        query_value = request.POST.get('tracking_id', '').strip()
        email = request.POST.get('email', '').strip()
        collection = get_collection('inquiries')
        if query_value:
            result = clean_doc(collection.find_one({'tracking_id': query_value}))
        if not result and email:
            matches = clean_docs(collection.find({'email': {'$regex': f'^{re.escape(email)}$', '$options': 'i'}}))
            matches.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
            result = matches[0] if matches else None
    return render(request, 'track_enquiry.html', {'result': result, 'searched': searched, 'tracking_id': query_value, 'email': email})


def feedback(request):
    if request.method == 'POST':
        payload, errors = _feedback_payload(request.POST)
        if errors:
            messages.error(request, 'Please complete these required fields: ' + ', '.join(errors))
            return render(request, 'feedback.html', {'form_data': payload, 'testimonials': _approved_testimonials()})
        payload['created_at'] = utc_now()
        payload['updated_at'] = utc_now()
        get_collection('testimonials').insert_one(payload)
        messages.success(request, 'Thank you for your feedback. It will appear after admin approval.')
        return redirect('feedback')
    return render(request, 'feedback.html', {'testimonials': _approved_testimonials()})


def admin_login(request):
    if request.session.get('admin_logged_in'):
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        if username == admin_username and password == admin_password:
            request.session['admin_logged_in'] = True
            request.session['admin_username'] = username
            messages.success(request, 'Welcome back to the AI-Solution dashboard.')
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'admin_login.html')


def admin_logout(request):
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')


@admin_required
def dashboard(request):
    collection = get_collection('inquiries')
    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    query = {}
    if search:
        query['$or'] = [
            {'tracking_id': {'$regex': search, '$options': 'i'}},
            {'name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'company_name': {'$regex': search, '$options': 'i'}},
            {'job_title': {'$regex': search, '$options': 'i'}},
        ]
    if status_filter and status_filter in STATUS_OPTIONS:
        query['status'] = status_filter
    inquiries = clean_docs(collection.find(query))
    inquiries.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
    all_docs = clean_docs(collection.find({}))
    for slug in CONTENT_MODULES:
        _seed_collection(slug)
    feedback_docs = clean_docs(get_collection('testimonials').find({}))
    chat_logs = clean_docs(get_collection('chat_logs').find({}))
    answered_chat = len([doc for doc in chat_logs if doc.get('matched_intent')])
    unanswered_chat = get_collection('unanswered_questions').count_documents({})
    context = {
        'inquiries': inquiries[:12],
        'search': search,
        'status_filter': status_filter,
        'status_options': STATUS_OPTIONS,
        'total_count': len(all_docs),
        'received_count': len([doc for doc in all_docs if doc.get('status') == 'Received']),
        'progress_count': len([doc for doc in all_docs if doc.get('status') == 'In Progress']),
        'completed_count': len([doc for doc in all_docs if doc.get('status') == 'Completed']),
        'chat_log_count': len(chat_logs),
        'unanswered_count': unanswered_chat,
        'pending_feedback_count': len([doc for doc in feedback_docs if doc.get('status') == 'Pending']),
        'status_chart': _count_by(all_docs, 'status', STATUS_OPTIONS),
        'service_chart': _count_by(all_docs, 'service_interest'),
        'chat_chart': [{'label': 'Answered', 'count': answered_chat, 'percent': int(answered_chat / max(answered_chat + unanswered_chat, 1) * 100)}, {'label': 'Unanswered', 'count': unanswered_chat, 'percent': int(unanswered_chat / max(answered_chat + unanswered_chat, 1) * 100)}],
        'feedback_chart': _count_by(feedback_docs, 'status', FEEDBACK_STATUS_OPTIONS),
        'recent_feedback': feedback_docs[-6:][::-1],
    }
    return render(request, 'dashboard.html', context)


@admin_required
def export_enquiries_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ai_solution_enquiries.csv"'
    writer = csv.writer(response)
    writer.writerow(['Tracking ID', 'Name', 'Email', 'Phone', 'Company', 'Country', 'Job Title', 'Service Interest', 'Budget', 'Status', 'Created'])
    for doc in clean_docs(get_collection('inquiries').find({})):
        writer.writerow([doc.get('tracking_id'), doc.get('name'), doc.get('email'), doc.get('phone'), doc.get('company_name'), doc.get('country'), doc.get('job_title'), doc.get('service_interest'), doc.get('budget_range'), doc.get('status'), doc.get('created_display')])
    return response


@admin_required
def inquiry_detail(request, inquiry_id):
    inquiry = clean_doc(get_collection('inquiries').find_one({'_id': make_id(inquiry_id)}))
    if not inquiry:
        raise Http404('Inquiry not found')
    return render(request, 'inquiry_detail.html', {'inquiry': inquiry, 'status_options': STATUS_OPTIONS})


@admin_required
def inquiry_status_update(request, inquiry_id):
    if request.method != 'POST':
        return redirect('inquiry_detail', inquiry_id=inquiry_id)

    status = request.POST.get('status', '').strip()
    admin_notes = request.POST.get('admin_notes', None)
    if status not in STATUS_OPTIONS:
        messages.error(request, 'Please choose a valid enquiry status.')
        return redirect(request.META.get('HTTP_REFERER') or 'dashboard')

    update_data = {'status': status, 'updated_at': utc_now()}
    if admin_notes is not None:
        update_data['admin_notes'] = admin_notes.strip()

    result = get_collection('inquiries').update_one({'_id': make_id(inquiry_id)}, {'$set': update_data})
    if getattr(result, 'modified_count', 0):
        messages.success(request, f'Enquiry status updated to {status}.')
    else:
        messages.warning(request, 'Status was already up to date or enquiry was not changed.')
    return redirect(request.META.get('HTTP_REFERER') or 'dashboard')


@admin_required
def inquiry_create(request):
    if request.method == 'POST':
        payload, errors = _inquiry_payload(request.POST)
        if errors:
            messages.error(request, 'Please complete these required fields: ' + ', '.join(errors))
            return render(request, 'inquiry_form.html', {'form_data': payload, 'status_options': STATUS_OPTIONS, 'mode': 'Create'})
        payload['created_at'] = utc_now()
        payload['updated_at'] = utc_now()
        get_collection('inquiries').insert_one(payload)
        messages.success(request, f'Enquiry created successfully with tracking ID {payload["tracking_id"]}.')
        return redirect('dashboard')
    return render(request, 'inquiry_form.html', {'status_options': STATUS_OPTIONS, 'mode': 'Create'})


@admin_required
def inquiry_edit(request, inquiry_id):
    collection = get_collection('inquiries')
    inquiry = clean_doc(collection.find_one({'_id': make_id(inquiry_id)}))
    if not inquiry:
        raise Http404('Inquiry not found')
    if request.method == 'POST':
        payload, errors = _inquiry_payload(request.POST)
        if errors:
            messages.error(request, 'Please complete these required fields: ' + ', '.join(errors))
            payload['id'] = inquiry_id
            return render(request, 'inquiry_form.html', {'form_data': payload, 'status_options': STATUS_OPTIONS, 'mode': 'Edit'})
        payload['tracking_id'] = inquiry.get('tracking_id') or payload.get('tracking_id') or _generate_tracking_id()
        payload['updated_at'] = utc_now()
        collection.update_one({'_id': make_id(inquiry_id)}, {'$set': payload})
        messages.success(request, 'Enquiry updated successfully.')
        return redirect('inquiry_detail', inquiry_id=inquiry_id)
    if not inquiry.get('tracking_id'):
        inquiry['tracking_id'] = _generate_tracking_id()
    return render(request, 'inquiry_form.html', {'form_data': inquiry, 'status_options': STATUS_OPTIONS, 'mode': 'Edit'})


@admin_required
def inquiry_delete(request, inquiry_id):
    collection = get_collection('inquiries')
    inquiry = clean_doc(collection.find_one({'_id': make_id(inquiry_id)}))
    if not inquiry:
        raise Http404('Inquiry not found')
    if request.method == 'POST':
        collection.delete_one({'_id': make_id(inquiry_id)})
        messages.success(request, 'Enquiry deleted successfully.')
        return redirect('dashboard')
    return render(request, 'confirm_delete.html', {'inquiry': inquiry})


@admin_required
def admin_content_list(request, module_slug):
    module = _module_or_404(module_slug)
    search = request.GET.get('q', '').strip().lower()
    docs = _get_content(module_slug)
    if search:
        docs = [doc for doc in docs if any(search in str(value).lower() for value in doc.values())]
    context = {'module_slug': module_slug, 'module': module, 'headers': [label for _key, label in module['list_fields']], 'rows': _table_rows(module, docs), 'search': search}
    return render(request, 'admin_content_list.html', context)


@admin_required
def admin_content_create(request, module_slug):
    module = _module_or_404(module_slug)
    if request.method == 'POST':
        payload, errors = _content_payload(module, request.POST, request.FILES)
        if errors:
            messages.error(request, 'Please fix: ' + ', '.join(errors))
            return render(request, 'admin_content_form.html', {'module_slug': module_slug, 'module': module, 'mode': 'Create', 'form_rows': _prepare_form_rows(module, payload), 'existing_images': payload.get('images', []), 'existing_images_json': json.dumps(payload.get('images', []))})
        payload['created_at'] = utc_now()
        payload['updated_at'] = utc_now()
        get_collection(module['collection']).insert_one(payload)
        messages.success(request, f'{module["singular"]} created successfully.')
        return redirect('admin_content_list', module_slug=module_slug)
    return render(request, 'admin_content_form.html', {'module_slug': module_slug, 'module': module, 'mode': 'Create', 'form_rows': _prepare_form_rows(module), 'existing_images': [], 'existing_images_json': '[]'})


@admin_required
def admin_content_edit(request, module_slug, item_id):
    module = _module_or_404(module_slug)
    collection = get_collection(module['collection'])
    item = clean_doc(collection.find_one({'_id': make_id(item_id)}))
    if not item:
        raise Http404('Item not found')
    if request.method == 'POST':
        payload, errors = _content_payload(module, request.POST, request.FILES, existing_item=item)
        if errors:
            messages.error(request, 'Please fix: ' + ', '.join(errors))
            return render(request, 'admin_content_form.html', {'module_slug': module_slug, 'module': module, 'mode': 'Edit', 'form_rows': _prepare_form_rows(module, payload), 'existing_images': payload.get('images', []), 'existing_images_json': json.dumps(payload.get('images', []))})
        payload['updated_at'] = utc_now()
        collection.update_one({'_id': make_id(item_id)}, {'$set': payload})
        messages.success(request, f'{module["singular"]} updated successfully.')
        return redirect('admin_content_list', module_slug=module_slug)
    existing_images = item.get('images', []) if module.get('supports_images') else []
    return render(request, 'admin_content_form.html', {'module_slug': module_slug, 'module': module, 'mode': 'Edit', 'form_rows': _prepare_form_rows(module, item), 'existing_images': existing_images, 'existing_images_json': json.dumps(existing_images)})


@admin_required
def admin_content_delete(request, module_slug, item_id):
    module = _module_or_404(module_slug)
    collection = get_collection(module['collection'])
    item = clean_doc(collection.find_one({'_id': make_id(item_id)}))
    if not item:
        raise Http404('Item not found')
    if request.method == 'POST':
        collection.delete_one({'_id': make_id(item_id)})
        messages.success(request, f'{module["singular"]} deleted successfully.')
        return redirect('admin_content_list', module_slug=module_slug)
    return render(request, 'admin_content_delete.html', {'module_slug': module_slug, 'module': module, 'item': item})


@admin_required
@require_POST
def testimonial_status(request, item_id, status):
    if status not in FEEDBACK_STATUS_OPTIONS:
        raise Http404('Invalid status')
    get_collection('testimonials').update_one({'_id': make_id(item_id)}, {'$set': {'status': status, 'updated_at': utc_now()}})
    messages.success(request, f'Feedback marked as {status}.')
    return redirect('admin_content_list', module_slug='testimonials')


@admin_required
def unanswered_questions(request):
    docs = clean_docs(get_collection('unanswered_questions').find({}))
    docs.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
    return render(request, 'unanswered_questions.html', {'questions': docs})


@admin_required
def unanswered_to_faq(request, question_id):
    collection = get_collection('unanswered_questions')
    question = clean_doc(collection.find_one({'_id': make_id(question_id)}))
    if not question:
        raise Http404('Question not found')
    if request.method == 'POST':
        answer = request.POST.get('answer', '').strip()
        intent = request.POST.get('intent', 'general').strip() or 'general'
        keywords = request.POST.get('keywords', '').strip()
        if not answer:
            messages.error(request, 'Please add an answer before saving the training record.')
            return render(request, 'unanswered_to_faq.html', {'question': question})
        get_collection('chatbot_faqs').insert_one({
            'question': question.get('message'),
            'intent': intent,
            'keywords': keywords or question.get('message'),
            'answer': answer,
            'priority': '8',
            'enabled': 'yes',
            'created_at': utc_now(),
            'updated_at': utc_now(),
        })
        collection.update_one({'_id': make_id(question_id)}, {'$set': {'status': 'Added to Training', 'answer': answer, 'updated_at': utc_now()}})
        messages.success(request, 'Question saved as a chatbot training record.')
        return redirect('unanswered_questions')
    return render(request, 'unanswered_to_faq.html', {'question': question})


@admin_required
@require_POST
def unanswered_delete(request, question_id):
    get_collection('unanswered_questions').delete_one({'_id': make_id(question_id)})
    messages.success(request, 'Unanswered question deleted.')
    return redirect('unanswered_questions')


def _normalise(text: str) -> str:
    text = str(text or '').lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return ' '.join(text.split())


def _tokens(text: str) -> List[str]:
    stop_words = {'what', 'when', 'where', 'why', 'how', 'do', 'does', 'is', 'are', 'am', 'i', 'you', 'your', 'we', 'our', 'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'and', 'or', 'can', 'could', 'please', 'tell', 'me', 'about', 'it', 'this', 'that'}
    return [word for word in _normalise(text).split() if word not in stop_words and len(word) > 1]


def _score_training(user_message: str, training: Dict) -> int:
    user_text = _normalise(user_message)
    user_words = set(_tokens(user_text))
    question = _normalise(training.get('question') or ' '.join(training.get('patterns', [])))
    answer = _normalise(training.get('answer', ''))
    intent = _normalise(training.get('intent', ''))
    raw_keywords = training.get('keywords', '')
    if isinstance(raw_keywords, list):
        keyword_words = set(_tokens(' '.join(raw_keywords)))
    else:
        keyword_words = set(_tokens(str(raw_keywords).replace(',', ' ')))
    question_words = set(_tokens(question))
    answer_words = set(_tokens(answer))
    score = 0
    if user_text and user_text in question:
        score += 14
    if intent and intent in user_words:
        score += 8
    score += len(user_words.intersection(keyword_words)) * 7
    score += len(user_words.intersection(question_words)) * 5
    score += len(user_words.intersection(answer_words)) * 2
    ratio = SequenceMatcher(None, user_text, question).ratio() if question else 0
    if ratio > 0.74:
        score += 10
    elif ratio > 0.55:
        score += 5
    try:
        score += int(training.get('priority', 0) or 0) // 2
    except ValueError:
        pass
    return score


@csrf_exempt
@require_POST
def chatbot_api(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'answer': 'Please send a valid message.'}, status=400)
    message = data.get('message', '').strip()
    if not message:
        return JsonResponse({'answer': 'Please type a question so I can help you.'})
    trainings = list(CODE_TRAINED_INTENTS)
    for faq in _get_content('chatbot'):
        if str(faq.get('enabled', 'yes')).lower() != 'no':
            trainings.append(faq)
    best = None
    best_score = 0
    for training in trainings:
        score = _score_training(message, training)
        if score > best_score:
            best = training
            best_score = score
    if best and best_score >= 6:
        response = best.get('answer')
        matched_intent = best.get('intent')
        was_answered = True
    else:
        response = 'I could not find an exact answer. Please submit your enquiry through the Contact page and our team will assist you shortly.'
        matched_intent = None
        was_answered = False
        get_collection('unanswered_questions').insert_one({'message': message, 'score': best_score, 'status': 'New', 'created_at': utc_now(), 'updated_at': utc_now()})
    get_collection('chat_logs').insert_one({'message': message, 'answer': response, 'score': best_score, 'matched_intent': matched_intent, 'was_answered': was_answered, 'created_at': utc_now()})
    return JsonResponse({'answer': response, 'score': best_score, 'intent': matched_intent, 'answered': was_answered})
