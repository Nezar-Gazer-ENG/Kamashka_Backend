from rest_framework import serializers
from .models import JobPosting, JobApplication, BlogPost

class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = '__all__'  # Includes all fields like expiration_date, salary_range, etc.


class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            'id',
            'job_posting',
            'full_name',
            'email',
            'phone',
            'nationality',
            'resume',
            'cover_letter',
            'application_date',
            'status',
        ]
        read_only_fields = ('application_date', 'status')


class BlogPostSerializer(serializers.ModelSerializer):
    published_date_formatted = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'slug',
            'excerpt',
            'content',
            'featured_image',
            'author',
            'category',
            'published_date',
            'published_date_formatted',
            'is_published',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_published_date_formatted(self, obj):
        return obj.published_date.strftime('%B %d, %Y') if obj.published_date else None
