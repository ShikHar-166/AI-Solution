from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from main import views

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('portfolio/<str:item_id>/', views.project_detail, name='project_detail'),
    path('gallery/', views.gallery, name='gallery'),
    path('gallery/<str:item_id>/', views.gallery_detail, name='gallery_detail'),
    path('events/', views.events, name='events'),
    path('events/<str:item_id>/', views.event_detail, name='event_detail'),
    path('articles/', views.articles, name='articles'),
    path('articles/<str:item_id>/', views.article_detail, name='article_detail'),
    path('contact/', views.contact, name='contact'),
    path('track-enquiry/', views.track_enquiry, name='track_enquiry'),
    path('feedback/', views.feedback, name='feedback'),

    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/export-enquiries/', views.export_enquiries_csv, name='export_enquiries_csv'),

    path('dashboard/enquiries/new/', views.inquiry_create, name='inquiry_create'),
    path('dashboard/enquiries/<str:inquiry_id>/', views.inquiry_detail, name='inquiry_detail'),
    path('dashboard/enquiries/<str:inquiry_id>/status/', views.inquiry_status_update, name='inquiry_status_update'),
    path('dashboard/enquiries/<str:inquiry_id>/edit/', views.inquiry_edit, name='inquiry_edit'),
    path('dashboard/enquiries/<str:inquiry_id>/delete/', views.inquiry_delete, name='inquiry_delete'),

    path('dashboard/unanswered-questions/', views.unanswered_questions, name='unanswered_questions'),
    path('dashboard/unanswered-questions/<str:question_id>/train/', views.unanswered_to_faq, name='unanswered_to_faq'),
    path('dashboard/unanswered-questions/<str:question_id>/delete/', views.unanswered_delete, name='unanswered_delete'),
    path('dashboard/testimonials/<str:item_id>/<str:status>/', views.testimonial_status, name='testimonial_status'),

    path('dashboard/<str:module_slug>/', views.admin_content_list, name='admin_content_list'),
    path('dashboard/<str:module_slug>/new/', views.admin_content_create, name='admin_content_create'),
    path('dashboard/<str:module_slug>/<str:item_id>/edit/', views.admin_content_edit, name='admin_content_edit'),
    path('dashboard/<str:module_slug>/<str:item_id>/delete/', views.admin_content_delete, name='admin_content_delete'),

    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)