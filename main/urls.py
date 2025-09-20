from django.urls import path
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Job postings
    path('job-postings/', views.JobPostingList.as_view(), name='jobposting-list'),
    path('job-postings/<int:pk>/', views.JobPostingDetail.as_view(), name='jobposting-detail'),

    # Job applications (standard form)
    path('job-applications/', views.submit_job_application, name='jobapplication-submit'),
    path('job-applications/<int:application_id>/resume/', views.serve_resume, name='jobapplication-resume'),

    # Blog
    path('blog-posts/', views.BlogPostList.as_view(), name='blogpost-list'),
    path('blog-posts/<slug:slug>/', views.BlogPostDetail.as_view(), name='blogpost-detail'),
    path('blog-categories/', views.blog_categories, name='blog-categories'),

    # Misc
    path('api-docs/', views.api_documentation, name='api-docs'),
    path('csrf-token/', views.get_csrf_token, name='csrf-token'),
    path('contact/', views.contact_view, name='contact'),
    path('test-email/', views.test_email_config, name='test-email'),
    path('debug-email/', views.debug_email_config, name='debug-email'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

