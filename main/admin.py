from django.contrib import admin
from django.utils.html import format_html
from .models import JobPosting, JobApplication, BlogPost

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'department',
        'employment_type',
        'is_active',
        'expiration_date',
        'created_at',
    )
    list_filter = ('is_active', 'department', 'employment_type', 'expiration_date')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_active',)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'email',
        'phone',
        'nationality',
        'job_posting',
        'application_date',
        'status',
        'resume_link',
    )
    list_filter = ('job_posting', 'application_date', 'status', 'nationality')
    search_fields = ('full_name', 'email', 'job_posting__title', 'nationality')
    readonly_fields = ('application_date',)
    list_editable = ('status',)

    def resume_link(self, obj):
        if obj.resume:
            return format_html('<a href="{}" target="_blank">Download Resume</a>', obj.resume.url)
        return "No resume"
    resume_link.short_description = 'Resume'


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
