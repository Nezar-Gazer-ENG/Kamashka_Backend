# management/commands/expire_jobs.py
# Create this file in: main/management/commands/expire_jobs.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from main.models import JobPosting

class Command(BaseCommand):
    help = 'Expire old job postings and send notifications about expiring jobs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually expiring jobs',
        )
        parser.add_argument(
            '--send-alerts',
            action='store_true',
            help='Send email alerts for jobs expiring soon',
        )
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=7,
            help='Days ahead to check for expiring jobs (default: 7)',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        send_alerts = options['send_alerts']
        days_ahead = options['days_ahead']

        # Find jobs that have expired
        expired_jobs = JobPosting.objects.filter(
            expires_at__lte=now,
            is_active=True
        )

        expired_count = expired_jobs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would expire {expired_count} job postings')
            )
            for job in expired_jobs:
                self.stdout.write(f'  - {job.title} (expired {job.expires_at})')
        else:
            # Actually expire the jobs
            expired_jobs.update(is_active=False)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully expired {expired_count} job postings')
            )

        # Find jobs expiring soon
        if send_alerts:
            expiring_soon = JobPosting.objects.filter(
                expires_at__gt=now,
                expires_at__lte=now + timedelta(days=days_ahead),
                is_active=True
            ).order_by('expires_at')

            expiring_count = expiring_soon.count()

            if expiring_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'Found {expiring_count} jobs expiring within {days_ahead} days')
                )

                # Send email alert
                try:
                    self.send_expiration_alert(expiring_soon, days_ahead)
                    self.stdout.write(
                        self.style.SUCCESS('Expiration alert email sent successfully')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send expiration alert: {str(e)}')
                    )
            else:
                self.stdout.write('No jobs expiring soon')

        # Summary
        total_active = JobPosting.objects.filter(is_active=True).count()
        total_expired = JobPosting.objects.filter(
            expires_at__lte=now
        ).count()

        self.stdout.write('\n--- Summary ---')
        self.stdout.write(f'Active job postings: {total_active}')
        self.stdout.write(f'Total expired job postings: {total_expired}')
        self.stdout.write(f'Jobs processed this run: {expired_count}')

    def send_expiration_alert(self, expiring_jobs, days_ahead):
        """Send email alert for jobs expiring soon"""
        subject = f'Job Postings Expiring Soon - {settings.COMPANY_NAME}'
        
        job_list = []
        for job in expiring_jobs:
            days_left = (job.expires_at - timezone.now()).days
            application_count = job.applications.count()
            job_list.append(
                f"• {job.title} ({job.department}) - {days_left} days left - {application_count} applications"
            )

        message = f"""
The following job postings will expire within the next {days_ahead} days:

{chr(10).join(job_list)}

Please review these postings and extend their expiration dates if needed.

You can manage job postings at: {settings.SITE_URL}/admin/main/jobposting/

This is an automated notification from your career management system.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONTACT_EMAIL],
            fail_silently=False,
        )


# management/commands/setup_sample_jobs.py
# Create this file in: main/management/commands/setup_sample_jobs.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from main.models import JobPosting, ApplicationQuestion

class Command(BaseCommand):
    help = 'Create sample job postings with custom questions for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing job postings before creating samples',
        )

    def handle(self, *args, **options):
        if options['clear_existing']:
            JobPosting.objects.all().delete()
            self.stdout.write('Cleared existing job postings')

        # Sample job postings
        jobs_data = [
            {
                'title': 'Senior Frontend Developer',
                'department': 'Engineering',
                'location': 'Remote',
                'employment_type': 'full_time',
                'salary_range': '$80,000 - $120,000',
                'description': 'We are looking for a Senior Frontend Developer to join our dynamic team. You will be responsible for building user-facing features using modern JavaScript frameworks.',
                'requirements': '''
• 5+ years of experience with React.js or Vue.js
• Strong knowledge of HTML5, CSS3, and JavaScript ES6+
• Experience with state management (Redux, Vuex)
• Familiarity with build tools (Webpack, Vite)
• Understanding of responsive design principles
• Experience with version control (Git)
                ''',
                'responsibilities': '''
• Develop and maintain frontend applications
• Collaborate with design and backend teams
• Optimize applications for maximum speed and scalability
• Participate in code reviews and technical discussions
• Mentor junior developers
                ''',
                'expires_in_days': 45,
                'questions': [
                    {
                        'question_text': 'What is your experience level with React.js?',
                        'question_type': 'select',
                        'options': 'Beginner (0-2 years),Intermediate (2-5 years),Advanced (5+ years)',
                        'is_required': True,
                        'order': 1
                    },
                    {
                        'question_text': 'Do you have experience with TypeScript?',
                        'question_type': 'checkbox',
                        'is_required': False,
                        'order': 2
                    },
                    {
                        'question_text': 'Please describe a challenging frontend project you worked on',
                        'question_type': 'textarea',
                        'is_required': True,
                        'order': 3
                    },
                    {
                        'question_text': 'Portfolio URL (if available)',
                        'question_type': 'text',
                        'placeholder_text': 'https://yourportfolio.com',
                        'is_required': False,
                        'order': 4
                    }
                ]
            },
            {
                'title': 'Digital Marketing Specialist',
                'department': 'Marketing',
                'location': 'New York, NY',
                'employment_type': 'full_time',
                'salary_range': '$50,000 - $70,000',
                'description': 'Join our marketing team to help drive growth through digital marketing campaigns, content creation, and data analysis.',
                'requirements': '''
• 3+ years of digital marketing experience
• Proficiency in Google Analytics and Google Ads
• Experience with social media marketing
• Content creation and copywriting skills
• Knowledge of SEO/SEM best practices
• Familiarity with marketing automation tools
                ''',
                'responsibilities': '''
• Plan and execute digital marketing campaigns
• Create engaging content for various channels
• Monitor and analyze campaign performance
• Manage social media presence
• Collaborate with design team on marketing materials
                ''',
                'expires_in_days': 30,
                'questions': [
                    {
                        'question_text': 'Which marketing channels have you worked with?',
                        'question_type': 'select',
                        'options': 'Social Media,Email Marketing,PPC Advertising,Content Marketing,SEO,All of the above',
                        'is_required': True,
                        'order': 1
                    },
                    {
                        'question_text': 'What is your preferred start date?',
                        'question_type': 'date',
                        'is_required': True,
                        'order': 2
                    },
                    {
                        'question_text': 'Do you have experience with marketing automation platforms?',
                        'question_type': 'checkbox',
                        'is_required': False,
                        'order': 3
                    }
                ]
            },
            {
                'title': 'UX/UI Designer',
                'department': 'Design',
                'location': 'San Francisco, CA',
                'employment_type': 'full_time',
                'salary_range': '$70,000 - $100,000',
                'description': 'We are seeking a talented UX/UI Designer to create intuitive and engaging user experiences for our digital products.',
                'requirements': '''
• 4+ years of UX/UI design experience
• Proficiency in Figma, Sketch, or Adobe Creative Suite
• Strong understanding of user-centered design principles
• Experience with prototyping and wireframing
• Knowledge of responsive and mobile design
• Portfolio demonstrating design process and thinking
                ''',
                'responsibilities': '''
• Design user interfaces and experiences
• Create wireframes, prototypes, and high-fidelity mockups
• Conduct user research and usability testing
• Collaborate with product and engineering teams
• Maintain and evolve design systems
                ''',
                'expires_in_days': 60,
                'questions': [
                    {
                        'question_text': 'Please provide a link to your design portfolio',
                        'question_type': 'text',
                        'is_required': True,
                        'order': 1
                    },
                    {
                        'question_text': 'Which design tools are you most comfortable with?',
                        'question_type': 'select',
                        'options': 'Figma,Sketch,Adobe XD,Adobe Creative Suite,Other',
                        'is_required': True,
                        'order': 2
                    },
                    {
                        'question_text': 'Describe your design process from research to final design',
                        'question_type': 'textarea',
                        'is_required': True,
                        'order': 3
                    },
                    {
                        'question_text': 'Upload a design case study (optional)',
                        'question_type': 'file',
                        'is_required': False,
                        'order': 4
                    }
                ]
            },
            {
                'title': 'Data Analyst Intern',
                'department': 'Analytics',
                'location': 'Remote',
                'employment_type': 'internship',
                'salary_range': '$15 - $20 per hour',
                'description': 'Summer internship opportunity for students interested in data analysis and business intelligence.',
                'requirements': '''
• Currently enrolled in relevant degree program
• Basic knowledge of SQL and Excel
• Familiarity with Python or R (preferred)
• Strong analytical and problem-solving skills
• Excellent communication skills
                ''',
                'responsibilities': '''
• Assist with data collection and cleaning
• Create reports and visualizations
• Support ongoing analytics projects
• Learn from experienced data scientists
• Present findings to stakeholders
                ''',
                'expires_in_days': 21,  # Shorter expiration for internship
                'questions': [
                    {
                        'question_text': 'What is your current year in school?',
                        'question_type': 'select',
                        'options': 'Freshman,Sophomore,Junior,Senior,Graduate Student',
                        'is_required': True,
                        'order': 1
                    },
                    {
                        'question_text': 'What is your major/field of study?',
                        'question_type': 'text',
                        'is_required': True,
                        'order': 2
                    },
                    {
                        'question_text': 'Do you have any programming experience?',
                        'question_type': 'textarea',
                        'placeholder_text': 'Please describe any programming languages or tools you have used',
                        'is_required': False,
                        'order': 3
                    },
                    {
                        'question_text': 'Expected graduation date',
                        'question_type': 'date',
                        'is_required': True,
                        'order': 4
                    }
                ]
            }
        ]

        created_count = 0
        for job_data in jobs_data:
            # Extract questions data
            questions_data = job_data.pop('questions', [])
            expires_in_days = job_data.pop('expires_in_days', 30)
            
            # Create job posting
            job_data['expires_at'] = timezone.now() + timedelta(days=expires_in_days)
            job = JobPosting.objects.create(**job_data)
            
            # Create questions
            for question_data in questions_data:
                ApplicationQuestion.objects.create(
                    job_posting=job,
                    **question_data
                )
            
            created_count += 1
            self.stdout.write(f'Created job: {job.title}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} sample job postings')
        )