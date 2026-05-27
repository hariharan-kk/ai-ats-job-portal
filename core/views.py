from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import JobPosting, Application
from .forms import ApplicationForm
from .utils import extract_text_from_pdf, evaluate_resume_with_local_model # <-- NEW IMPORT
from django.contrib.auth import login
from .forms import CandidateRegistrationForm
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Question, CandidateTest
from django.urls import reverse

def job_list(request):
    jobs = JobPosting.objects.filter(is_active=True).order_by('-posting_date')
    return render(request, 'core/job_list.html', {'jobs': jobs})

@login_required
def apply_for_job(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id)
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES) 
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.candidate = request.user
            
            # --- PHASE C: AI EVALUATION TRIGGER ---
            # 1. Extract text
            extracted_text = extract_text_from_pdf(request.FILES['resume'])
            application.extracted_text = extracted_text
            
            # 2. Send to Gemini if text was successfully extracted
            if extracted_text:
                score, justification = evaluate_resume_with_local_model(extracted_text, job.core_requirements)
                application.ai_match_score = score
                application.ai_justification = justification
                
                # 3. Auto-update status based on threshold (e.g., 75%)
                if score >= 75:
                    application.status = 'Shortlisted'
                else:
                    application.status = 'Rejected'
            
            # Save the final application with all AI data attached
            application.save()
            # 1. Create the blank test record in the database
            test_instance = CandidateTest.objects.create(application=application)
            # 2. Build the absolute URL (e.g., http://127.0.0.1:8000/test/uuid-here/)
            test_url = request.build_absolute_uri(
                reverse('take_aptitude_test', args=[test_instance.secure_id])
            )
            # 3. Email the candidate their secure link
            subject = f"Required: Aptitude Test for {job.title}"
            message = f"""
            Hi {request.user.username},

            Thank you for applying. Before we proceed with your AI application review, please complete the required technical aptitude test. 

            Click your secure, one-time link below to begin:
            {test_url}

            Best of luck,
            The HR Team
            """
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [request.user.email],
                fail_silently=False,
            )

            
            # --- NEW EMAIL NOTIFICATION LOGIC ---
            # We check the status we just saved to format the email text
            status_text = "Shortlisted! 🎉" if application.status == 'Shortlisted' else "Not Selected at this time."
            # Fallback to 0.0 if score wasn't calculated
            final_score = application.ai_match_score if application.ai_match_score else 0.0
            
            subject = f'Application Received: {job.title}'
            message = f"""
Hello {request.user.username},

Thank you for applying for the {job.title} position!
            
Our AI system has successfully reviewed your resume and calculated a match score of {final_score}%.
            
Based on this score, your application is {status_text}
            
We will be in touch soon with next steps.
            
Best regards,
The AI Job Portal Team
"""
            try:
                # This actually sends the email via Google SMTP
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[request.user.email], 
                    fail_silently=False, 
                )
            except Exception as e:
                # If the email fails (e.g. wrong password), it prints to terminal but doesn't crash the site
                print(f"Failed to send email: {e}")
            # --- END EMAIL LOGIC ---
            
            # Let's redirect them straight to their dashboard so they can see the new application!
            return redirect('dashboard')
    else:
        form = ApplicationForm()
        
    return render(request, 'core/apply.html', {'form': form, 'job': job})

def register_candidate(request):
    if request.method == 'POST':
        form = CandidateRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_candidate = True # Explicitly mark them as a candidate, not HR
            user.save()
            login(request, user) # Auto-login after registering
            return redirect('job_list')
    else:
        form = CandidateRegistrationForm()
        
    return render(request, 'core/register.html', {'form': form})

@login_required
def candidate_dashboard(request):
    # Fetch applications specifically for the logged-in user, newest first
    user_applications = Application.objects.filter(candidate=request.user).order_by('-applied_at')
    
    return render(request, 'core/dashboard.html', {'applications': user_applications})

def job_detail(request, job_id):
    # Fetch the specific job or return a 404 if it doesn't exist
    job = get_object_or_404(JobPosting, id=job_id)
    return render(request, 'core/job_detail.html', {'job': job})

def take_aptitude_test(request, secure_id):
    """Displays the test to the candidate and auto-grades it upon submission."""
    # Find the specific test using the secure UUID from the URL
    test_instance = get_object_or_404(CandidateTest, secure_id=secure_id)
    
    # SECURITY: If they already took it, block them from taking it again
    if test_instance.is_completed:
        return render(request, 'core/test_already_completed.html')
        
    # Grab all the questions HR created in the database
    questions = Question.objects.all()
    
    if request.method == 'POST':
        correct_answers = 0
        total_questions = questions.count()
        
        # The Auto-Grader loop
        for q in questions:
            # Check what the user selected (HTML input names will be "question_1", "question_2", etc.)
            user_choice = request.POST.get(f'question_{q.id}') 
            if user_choice == q.correct_answer:
                correct_answers += 1
                
        # Calculate the final percentage (0 to 100)
        final_score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0
        
        # Save the results to the database for HR to see
        test_instance.score = final_score
        test_instance.is_completed = True
        test_instance.completed_at = timezone.now()
        test_instance.save()
        
        return render(request, 'core/test_success.html', {'score': final_score})
        
    # If it's a GET request, just show them the test form
    return render(request, 'core/take_test.html', {'questions': questions, 'test_instance': test_instance})