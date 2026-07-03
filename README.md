# AI-Solution Website

A professional Python Django, MongoDB Atlas, HTML, CSS and JavaScript website for AI-Solution using a teal and blue business landing theme.

## Included features

- Professional home page with AI business branding
- Services page
- Portfolio and project detail pages
- Separate gallery page and gallery detail pages
- Separate events page and event detail pages
- Articles and article detail pages
- Contact enquiry form with automatic tracking ID
- Public enquiry tracking page
- MongoDB Atlas storage through `MONGODB_URI`
- Password-protected admin dashboard with sidebar navigation
- Customer enquiry CRUD and admin-controlled status updates
- Dashboard summary cards and clean visual charts
- Services CRUD
- Portfolio CRUD
- Gallery CRUD with multiple image upload
- Events CRUD with multiple image upload
- Articles CRUD with image upload
- Public feedback submission page
- Admin approval system for testimonials
- Chatbot training CRUD
- Improved chatbot fallback response
- Unanswered chatbot questions stored for admin review
- Ability to convert unanswered questions into chatbot training records
- Chat logs stored in database
- CSV export for enquiries
- Responsive HTML/CSS/JS frontend

## Local setup

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
copy .env.example .env
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Admin login:

```text
Username: admin
Password: admin123
```

## MongoDB Atlas

Paste your MongoDB Atlas URI into `.env`:

```env
MONGODB_URI=mongodb+srv://your_user:your_password@your_cluster.mongodb.net/ai_solution?retryWrites=true&w=majority
```

If `MONGODB_URI` is not set, the project uses `local_preview_db.json` for local testing.

## Render deployment

Use these values on Render:

Build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Start command:

```bash
gunicorn core.wsgi:application
```

Add environment variables:

```env
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
MONGODB_URI=your-mongodb-atlas-connection-string
```
