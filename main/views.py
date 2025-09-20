from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, parser_classes, renderer_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import TemplateHTMLRenderer
from django.core.mail import EmailMessage, send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.conf import settings
from django.http import FileResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie  # Added ensure_csrf_cookie

import json
import re

from .models import JobPosting, JobApplication, BlogPost
from .serializers import JobPostingSerializer, BlogPostSerializer, JobApplicationSerializer


# ------------------- Job Posting -------------------

class JobPostingList(generics.ListAPIView):
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        now = timezone.now()
        return JobPosting.objects.filter(
            is_active=True
        ).filter(
            expiration_date__isnull=True
        ) | JobPosting.objects.filter(
            is_active=True,
            expiration_date__gt=now
        )


class JobPostingDetail(generics.RetrieveAPIView):
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        now = timezone.now()
        return JobPosting.objects.filter(is_active=True).filter(
            expiration_date__isnull=True
        ) | JobPosting.objects.filter(
            is_active=True,
            expiration_date__gt=now
        )


# ------------------- Job Applications -------------------

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def submit_job_application(request):
    serializer = JobApplicationSerializer(data=request.data)

    if serializer.is_valid():
        application = serializer.save()

        try:
            # Confirmation email to applicant
            applicant_context = {
                'applicant_name': application.full_name,
                'job_title': application.job_posting.title,
                'company_name': settings.COMPANY_NAME
            }

            applicant_email_body = render_to_string(
                'emails/job_application_confirmation.html', applicant_context
            )

            applicant_email = EmailMessage(
                f'Application Received: {application.job_posting.title} - {settings.COMPANY_NAME}',
                applicant_email_body,
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                reply_to=[settings.DEFAULT_FROM_EMAIL],
            )
            applicant_email.content_subtype = "html"
            applicant_email.send()

            # Notification email to admin
            admin_subject = f'New Job Application: {application.job_posting.title}'
            admin_message = f"""
            New Job Application Received:

            Position: {application.job_posting.title}
            Applicant: {application.full_name}
            Email: {application.email}
            Phone: {application.phone}
            Nationality: {application.nationality or "Not provided"}

            Cover Letter:
            {application.cover_letter or 'No cover letter provided'}

            Application Date: {application.application_date.strftime('%Y-%m-%d %H:%M')}

            View in Admin: {request.build_absolute_uri(
                reverse('admin:main_jobapplication_change', args=[application.id])
            )}
            """

            send_mail(
                admin_subject,
                admin_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],
                fail_silently=False,
            )

        except Exception as e:
            print(f"Email sending failed: {e}")  # Don't break flow if email fails

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@require_GET
def serve_resume(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)
    resume_file = application.resume

    response = FileResponse(resume_file.open(), as_attachment=True)
    response['Content-Disposition'] = (
        f'attachment; filename="{application.full_name} - Resume.{resume_file.name.split(".")[-1]}"'
    )
    return response


# ------------------- Blog -------------------

class BlogPostList(generics.ListAPIView):
    serializer_class = BlogPostSerializer

    def get_queryset(self):
        queryset = BlogPost.objects.filter(is_published=True).order_by('-published_date', '-created_at')

        # Filters from query params
        category = self.request.query_params.get('category')
        author = self.request.query_params.get('author')
        search = self.request.query_params.get('search')

        if category:
            queryset = queryset.filter(category__iexact=category)

        if author:
            queryset = queryset.filter(author__icontains=author)

        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(content__icontains=search)

        return queryset


class BlogPostDetail(generics.RetrieveAPIView):
    serializer_class = BlogPostSerializer
    lookup_field = 'slug'

    def get_object(self):
        slug = self.kwargs.get('slug')

        # Try slug first
        try:
            return get_object_or_404(BlogPost, slug=slug, is_published=True)
        except Http404:
            # Fallback to ID if slug not found
            try:
                blog_id = int(slug)
                return get_object_or_404(BlogPost, id=blog_id, is_published=True)
            except (ValueError, Http404):
                raise Http404("Blog post not found")


@api_view(['GET'])
def blog_categories(request):
    try:
        categories = BlogPost.objects.values_list('category', flat=True).distinct()
        return Response(categories)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------- Utilities -------------------

@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer])
def api_documentation(request):
    return Response(template_name='api_documentation.html')


@require_GET
@ensure_csrf_cookie  # Added this decorator
def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_POST
def contact_view(request):  # Removed @csrf_exempt - let Django handle CSRF properly
    if request.method == 'POST':
        try:
            # Check if it's JSON data (from React)
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                    name = data.get('name', '').strip()
                    email = data.get('email', '').strip()
                    subject = data.get('subject', '').strip()
                    message = data.get('message', '').strip()
                except json.JSONDecodeError:
                    return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)
            else:
                # Fallback to form data
                name = request.POST.get('name', '').strip()
                email = request.POST.get('email', '').strip()
                subject = request.POST.get('subject', '').strip()
                message = request.POST.get('message', '').strip()

            # Validate required fields
            validation_errors = []
            if not name:
                validation_errors.append('Name is required.')
            if not email:
                validation_errors.append('Email is required.')
            elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                validation_errors.append('Please enter a valid email address.')
            if not subject:
                validation_errors.append('Subject is required.')
            if not message:
                validation_errors.append('Message is required.')

            if validation_errors:
                return JsonResponse({'success': False, 'error': ' '.join(validation_errors)}, status=400)

            # Email: Notification to YOUR inbox
            admin_subject = f"Website Contact: {subject}"
            admin_message = f"""
            New contact form submission from your website:
            
            From: {name} <{email}>
            Subject: {subject}
            
            Message:
            {message}
            
            ---
            This message was sent from your website contact form.
            """

            send_mail(
                admin_subject,
                admin_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],
                fail_silently=False,
            )

            return JsonResponse({'success': True})

        except BadHeaderError:
            return JsonResponse({'success': False, 'error': 'Invalid header found. Please try again.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': 'An unexpected error occurred. Please try again later.'}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method. Only POST requests are allowed.'}, status=405)


@require_GET
@csrf_exempt  # Keep this for testing endpoints
def test_email_config(request):
    try:
        # Test 1: Send email to admin
        send_mail(
            'Test Email from Django - Admin',
            'This is a test email to verify your admin email configuration is working.',
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONTACT_EMAIL],
            fail_silently=False,
        )

        # Test 2: Send email to a test user
        test_user_email = request.GET.get('test_email', 'test@example.com')
        send_mail(
            'Test Email from Django - User',
            'This is a test email to verify your user email configuration is working.',
            settings.DEFAULT_FROM_EMAIL,
            [test_user_email],
            fail_silently=False,
        )

        return JsonResponse({
            'success': True,
            'message': f'Test emails sent successfully! Check both {settings.CONTACT_EMAIL} and {test_user_email}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'config': {
                'EMAIL_HOST': settings.EMAIL_HOST,
                'EMAIL_PORT': settings.EMAIL_PORT,
                'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
                'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
                'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
                'CONTACT_EMAIL': settings.CONTACT_EMAIL,
            }
        }, status=500)


@require_GET
@csrf_exempt  # Keep this for testing endpoints
def debug_email_config(request):
    try:
        config = {
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
            'CONTACT_EMAIL': settings.CONTACT_EMAIL,
            'COMPANY_NAME': settings.COMPANY_NAME,
        }

        # Test 1: Send email to company inbox
        send_mail(
            'Test 1: Django to Company Email',
            f'This is a test email to your company inbox.\n\nTime: {timezone.now()}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONTACT_EMAIL],
            fail_silently=False,
        )

        # Test 2: Send email to personal email
        personal_email = request.GET.get('personal_email', 'your-personal@gmail.com')
        send_mail(
            'Test 2: Django to Personal Email',
            f'This is a test email to your personal inbox.\n\nTime: {timezone.now()}',
            settings.DEFAULT_FROM_EMAIL,
            [personal_email],
            fail_silently=False,
        )

        return JsonResponse({
            'success': True,
            'message': 'Test emails sent successfully!',
            'config': config
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'config': {
                'EMAIL_HOST': settings.EMAIL_HOST,
                'EMAIL_PORT': settings.EMAIL_PORT,
                'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
                'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
                'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
                'CONTACT_EMAIL': settings.CONTACT_EMAIL,
            }
        }, status=500)


# ------------------- Maintenance -------------------

def deactivate_expired_job_postings():
    expired_jobs = JobPosting.objects.filter(is_active=True, expiration_date__lte=timezone.now())
    expired_jobs.update(is_active=False)