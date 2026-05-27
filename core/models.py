from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail # NEW IMPORT
from django.conf import settings
import uuid

# 1. Extended User Model
class User(AbstractUser):
    is_hr = models.BooleanField(default=False, help_text="Designates whether the user is an HR/Admin.")
    is_candidate = models.BooleanField(default=True, help_text="Designates whether the user is a standard applicant.")

    # Fix for reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='core_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='core_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

# 2. Job Posting Model
class JobPosting(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    core_requirements = models.TextField(help_text="Paste the job requirements here for the AI to evaluate against.")
    posting_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

# 3. Application Model
class Application(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending AI Review'),
        ('Shortlisted', 'Shortlisted by AI'),
        ('AI Rejected', 'Rejected by AI'),
        ('HR Interviewing', 'HR Interviewing'),
        ('Hired', 'Hired! 🎉'),
        ('Final Reject', 'Not Selected'),
    )
    
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_candidate': True})
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    resume = models.FileField(upload_to='resumes/', help_text="Upload PDF resume.")
    ai_match_score = models.FloatField(blank=True, null=True, help_text="Percentage match returned by Gemini.")
    ai_justification = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True, null=True, help_text="Raw text extracted from the PDF for HR keyword searching.")

    # --- NEW INTERVIEW FIELDS ---
    interview_time = models.DateTimeField(null=True, blank=True, help_text="Set the date and time for the interview")
    interview_venue = models.CharField(max_length=255, null=True, blank=True, help_text="Zoom link, Google Meet, or physical address")



    # --- NEW AUTOMATION LOGIC ---
    def save(self, *args, **kwargs):
        # Only check for changes if the application already exists in the database
        if self.pk: 
            old_application = Application.objects.get(pk=self.pk)
            
            # Check if HR just changed the status to 'HR Interviewing'
            if old_application.status != 'HR Interviewing' and self.status == 'HR Interviewing':
                
                # Draft the Interview Invitation Email
                subject = f"Interview Invitation: {self.job.title}"
                
                # Format the date nicely if it exists, otherwise leave a placeholder
                time_str = self.interview_time.strftime("%B %d, %Y at %I:%M %p") if self.interview_time else "TBD"
                venue_str = self.interview_venue if self.interview_venue else "TBD"
                
                message = f"""
Hello {self.candidate.username},

Congratulations! You have been shortlisted and we would love to invite you for an interview for the {self.job.title} position.

Here are your interview details:
- Date & Time: {time_str}
- Venue / Link: {venue_str}

Please let us know if you need to reschedule.

Best regards,
The HR Team
"""
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[self.candidate.email],
                        fail_silently=False,
                    )
                    print(f"Interview email sent to {self.candidate.email}")
                except Exception as e:
                    print(f"Failed to send interview email: {e}")

        # Finally, save the application to the database normally
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.candidate.username} applied for {self.job.title}"
    

class Question(models.Model):
    """Stores the multiple-choice questions created by HR"""
    text = models.CharField(max_length=500, help_text="The question you want to ask.")
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    
    CORRECT_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]
    correct_answer = models.CharField(max_length=1, choices=CORRECT_CHOICES)

    def __str__(self):
        return self.text

class CandidateTest(models.Model):
    """Generates a secure link for the candidate and stores their final score"""
    # NOTE: Change 'Application' to match whatever your candidate model is named!
    application = models.OneToOneField('Application', on_delete=models.CASCADE, related_name='aptitude_test')
    
    # This creates the secure, unguessable link (e.g., website.com/test/123e4567-e89b-12d3...)
    secure_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    is_completed = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Aptitude Test for {self.application}"