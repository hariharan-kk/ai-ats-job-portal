from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q

import requests
import os
import re

from .models import JobPosting, Application, Question, CandidateTest
from .forms import ApplicationForm, CandidateRegistrationForm
from .utils import extract_text_from_pdf, evaluate_resume_with_local_model, generate_custom_questions

# ==========================================
# --- THE AI ROUTER (ADAPTER PATTERN) ---
# ==========================================
# Change to True if mentor wants Ollama again
USE_OLLAMA = False 

def evaluate_with_huggingface(resume_text, core_requirements):
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    hf_token = os.environ.get("HF_TOKEN", "YOUR_HUGGINGFACE_ACCESS_TOKEN_HERE")
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    prompt = f"<s>[INST] You are an expert HR assistant. Evaluate this resume against these requirements: {core_requirements}. Resume: {resume_text} Provide a match score (0-100) on the first line as just a number, followed by a brief justification. [/INST]"
    
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 250, "temperature": 0.3, "return_full_text": False}
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            ai_output = result[0].get('generated_text', '').strip()
            
            # Default fallback values
            score = 0
            justification = ai_output
            
            # Safely extract the first number from the AI's response to use as the score
            match = re.search(r'\b(\d{1,3})\b', ai_output)
            if match:
                score = int(match.group(1))
                # Remove the raw number from the beginning of the justification text
                justification = ai_output.replace(match.group(1), '', 1).strip()
                
            return score, justification
            
        return 0, "Evaluation failed to generate."
    except Exception as e:
        print(f"Hugging Face API Error: {e}")
        return 0, "Error connecting to AI evaluation server."

def process_resume_evaluation(resume_text, core_requirements):
    """Routes the AI evaluation to either local Ollama or cloud Hugging Face"""
    if USE_OLLAMA:
        print("Routing to local Ollama from utils...")
        return evaluate_resume_with_local_model(resume_text, core_requirements)
    else:
        print("Routing to Hugging Face Cloud API...")
        return evaluate_with_huggingface(resume_text, core_requirements)

# ==========================================
# --- DJANGO VIEWS ---
# ==========================================

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
            extracted_text = extract_text_from_pdf(request.FILES['resume'])
            application.extracted_text = extracted_text
            
            if extracted_text:
                # WE CHANGED THIS LINE: Now it calls our Router instead of hardcoding Ollama!
                score, justification = process_resume_evaluation(extracted_text, job.core_requirements)
                
                application.ai_match_score = score
                application.ai_justification = justification
                
                if score >= 50:
                    application.status = 'Shortlisted'
                else:
                    application.status = 'Rejected'
            
            application.save()
            
            # --- PHASE D: DYNAMIC EXAM GENERATION ---
            if application.status == 'Shortlisted':
                test_instance = CandidateTest.objects.create(application=application)
                custom_questions = generate_custom_questions(extracted_text)
                
                if custom_questions:
                    if isinstance(custom_questions, dict):
                        found_list = False
                        for key, value in custom_questions.items():
                            if isinstance(value, list):
                                custom_questions = value
                                found_list = True
                                break
                        
                        if not found_list:
                            first_val = next(iter(custom_questions.values()), None)
                            if isinstance(first_val, dict) and ('text' in first_val or 'question' in first_val):
                                custom_questions = list(custom_questions.values())
                            else:
                                custom_questions = [custom_questions]
                    
                    if isinstance(custom_questions, list):
                        for q in custom_questions:
                            if isinstance(q, dict):
                                Question.objects.create(
                                    test=test_instance, 
                                    text=q.get('text') or q.get('question') or 'Error generating question',
                                    option_a=q.get('option_a', 'Option A'),
                                    option_b=q.get('option_b', 'Option B'),
                                    option_c=q.get('option_c', 'Option C'),
                                    option_d=q.get('option_d', 'Option D'),
                                    correct_answer=q.get('correct_answer', 'A')
                                )

                test_url = request.build_absolute_uri(
                    reverse('take_aptitude_test', args=[test_instance.secure_id])
                )
                
                subject = f"Required: Technical Aptitude Test for {job.title}"
                message = f"Hi {request.user.username},\n\nCongratulations! Your resume has passed our initial AI screening.\nWe have dynamically generated a technical aptitude test based on the specific skills listed in your resume.\n\nClick your secure, one-time link below to begin:\n{test_url}\n\nBest of luck,\nThe HR Team"
                
                try:
                    send_mail(
                        subject, message, settings.EMAIL_HOST_USER, [request.user.email], fail_silently=False,
                    )
                except Exception as e:
                    print(f"Failed to send aptitude test email: {e}")

            # --- EMAIL NOTIFICATION LOGIC ---
            status_text = "Shortlisted! 🎉 Please check your email for a technical assessment." if application.status == 'Shortlisted' else "Not Selected at this time."
            final_score = application.ai_match_score if application.ai_match_score else 0.0
            
            subject = f'Application Received: {job.title}'
            message = f"Hello {request.user.username},\n\nThank you for applying for the {job.title} position!\n\nOur AI system has successfully reviewed your resume and calculated a match score of {final_score}%.\n\nBased on this score, your application is {status_text}\n\nBest regards,\nThe AI Job Portal Team"
            
            try:
                send_mail(
                    subject=subject, message=message, from_email=settings.EMAIL_HOST_USER, recipient_list=[request.user.email], fail_silently=False, 
                )
            except Exception as e:
                print(f"Failed to send status email: {e}")
            
            return redirect('dashboard')
    else:
        form = ApplicationForm()
        
    return render(request, 'core/apply.html', {'form': form, 'job': job})

def register_candidate(request):
    if request.method == 'POST':
        form = CandidateRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_candidate = True 
            user.save()
            login(request, user) 
            return redirect('job_list')
    else:
        form = CandidateRegistrationForm()
        
    return render(request, 'core/register.html', {'form': form})

@login_required
def candidate_dashboard(request):
    user_applications = Application.objects.filter(candidate=request.user).order_by('-applied_at')
    return render(request, 'core/dashboard.html', {'applications': user_applications})

def job_detail(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id)
    return render(request, 'core/job_detail.html', {'job': job})

def take_aptitude_test(request, secure_id):
    test_instance = get_object_or_404(CandidateTest, secure_id=secure_id)
    
    if test_instance.is_completed:
        return render(request, 'core/test_already_completed.html')
        
    questions = Question.objects.filter(test=test_instance)
    
    if request.method == 'POST':
        correct_answers = 0
        total_questions = questions.count()
        
        for q in questions:
            user_choice = request.POST.get(f'question_{q.id}') 
            if user_choice == q.correct_answer:
                correct_answers += 1
                
        final_score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0
        
        test_instance.score = final_score
        test_instance.is_completed = True
        test_instance.completed_at = timezone.now()
        test_instance.save()
        
        return render(request, 'core/test_success.html', {'score': final_score})
        
    return render(request, 'core/take_test.html', {'questions': questions, 'test_instance': test_instance})

def is_hr_or_superuser(user):
    return user.is_superuser or getattr(user, 'is_hr', False) or user.groups.filter(name='HR').exists()

@login_required(login_url='/login/') 
@user_passes_test(is_hr_or_superuser, login_url='/login/')
def custom_hr_dashboard(request):
    app_search_query = request.GET.get('q', '') 
    job_search_query = request.GET.get('job_q', '') 
    
    if job_search_query:
        recent_jobs = JobPosting.objects.filter(
            Q(title__icontains=job_search_query) | Q(core_requirements__icontains=job_search_query)
        ).order_by('-posting_date')
    else:
        recent_jobs = JobPosting.objects.all().order_by('-posting_date')[:5]

    if app_search_query:
        recent_applications = Application.objects.filter(
            Q(candidate__username__icontains=app_search_query) |
            Q(job__title__icontains=app_search_query) |
            Q(extracted_text__icontains=app_search_query)
        ).order_by('-applied_at')
    else:
        recent_applications = Application.objects.all().order_by('-applied_at')[:10]
    
    context = {
        'recent_jobs': recent_jobs,
        'recent_applications': recent_applications,
        'search_query': app_search_query,
        'job_search_query': job_search_query,
    }
    return render(request, 'core/hr_dashboard.html', context)

@login_required(login_url='/login/')
@user_passes_test(is_hr_or_superuser, login_url='/login/')
def hr_application_detail(request, app_id):
    application = get_object_or_404(Application, id=app_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        interview_time = request.POST.get('interview_time')
        interview_venue = request.POST.get('interview_venue')
        
        if new_status:
            application.status = new_status
        if interview_time:
            application.interview_time = interview_time
        if interview_venue:
            application.interview_venue = interview_venue
            
        application.save() 
        return redirect('hr_dashboard') 

    try:
        candidate_test = CandidateTest.objects.get(application=application)
    except CandidateTest.DoesNotExist:
        candidate_test = None

    context = {
        'app': application,
        'test': candidate_test,
        'status_choices': Application.STATUS_CHOICES, 
    }
    return render(request, 'core/hr_application_detail.html', context)

@login_required(login_url='/login/')
@user_passes_test(is_hr_or_superuser, login_url='/login/')
def add_job_posting(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        core_requirements = request.POST.get('core_requirements')
        
        JobPosting.objects.create(
            title=title,
            description=description,
            core_requirements=core_requirements,
            is_active=True 
        )
        return redirect('hr_dashboard')
        
    return render(request, 'core/add_job.html')