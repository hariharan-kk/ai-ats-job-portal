from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import JobPosting, Application
from .forms import ApplicationForm
from .utils import extract_text_from_pdf, evaluate_resume_with_gemini # <-- NEW IMPORT
from django.contrib.auth import login
from .forms import CandidateRegistrationForm
from django.core.mail import send_mail
from django.conf import settings

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
                score, justification = evaluate_resume_with_gemini(extracted_text, job.core_requirements)
                application.ai_match_score = score
                application.ai_justification = justification
                
                # 3. Auto-update status based on threshold (e.g., 75%)
                if score >= 75:
                    application.status = 'Shortlisted'
                else:
                    application.status = 'Rejected'
            
            # Save the final application with all AI data attached
            application.save()
            
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