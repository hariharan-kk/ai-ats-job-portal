from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import JobPosting, Application
from .forms import ApplicationForm
from .utils import extract_text_from_pdf, evaluate_resume_with_local_model, generate_custom_questions
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
            
            # 2. Send to Gemini/Qwen if text was successfully extracted
            if extracted_text:
                score, justification = evaluate_resume_with_local_model(extracted_text, job.core_requirements)
                application.ai_match_score = score
                application.ai_justification = justification
                
                # 3. Auto-update status based on the Gatekeeper
                if score >= 50:
                    application.status = 'Shortlisted'
                else:
                    application.status = 'Rejected'
            
            # Save the final application with all AI data attached
            application.save()
            
            # --- PHASE D: DYNAMIC EXAM GENERATION (Only if Shortlisted!) ---
            if application.status == 'Shortlisted':
                # 1. Create the blank test record in the database
                test_instance = CandidateTest.objects.create(application=application)
                
                # 2. Ask Qwen to generate custom JSON questions based on the resume
                custom_questions = generate_custom_questions(extracted_text)
                
                if custom_questions:
                    # --- AI SAFETY NET ---
                    if isinstance(custom_questions, dict):
                        # Scenario A: Qwen wrapped the list in a parent dictionary (e.g., {"questions": [...]})
                        found_list = False
                        for key, value in custom_questions.items():
                            if isinstance(value, list):
                                custom_questions = value
                                found_list = True
                                break
                        
                        if not found_list:
                            # Scenario C: Qwen structured it as nested objects (e.g., {"question1": {...}, "question2": {...}})
                            first_val = next(iter(custom_questions.values()), None)
                            if isinstance(first_val, dict) and ('text' in first_val or 'question' in first_val):
                                custom_questions = list(custom_questions.values())
                            else:
                                # Scenario B: Qwen just gave us ONE single question dictionary! Wrap it in a list.
                                custom_questions = [custom_questions]
                    
                    # 2. Only proceed if we definitely have a list now
                    if isinstance(custom_questions, list):
                        # 3. Loop through the AI's JSON array and save them to the database
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

                # 4. Build the absolute URL for the test
                test_url = request.build_absolute_uri(
                    reverse('take_aptitude_test', args=[test_instance.secure_id])
                )
                
                # 5. Email the candidate their custom secure link
                subject = f"Required: Technical Aptitude Test for {job.title}"
                message = f"""
Hi {request.user.username},

Congratulations! Your resume has passed our initial AI screening. 
We have dynamically generated a technical aptitude test based on the specific skills listed in your resume. 

Click your secure, one-time link below to begin:
{test_url}

Best of luck,
The HR Team
"""
                try:
                    send_mail(
                        subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Failed to send aptitude test email: {e}")

            
            # --- EMAIL NOTIFICATION LOGIC (For everyone) ---
            status_text = "Shortlisted! 🎉 Please check your email for a technical assessment." if application.status == 'Shortlisted' else "Not Selected at this time."
            final_score = application.ai_match_score if application.ai_match_score else 0.0
            
            subject = f'Application Received: {job.title}'
            message = f"""
Hello {request.user.username},

Thank you for applying for the {job.title} position!
            
Our AI system has successfully reviewed your resume and calculated a match score of {final_score}%.
            
Based on this score, your application is {status_text}
            
Best regards,
The AI Job Portal Team
"""
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[request.user.email], 
                    fail_silently=False, 
                )
            except Exception as e:
                print(f"Failed to send status email: {e}")
            
            # Redirect to dashboard
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
    """Displays the test to the candidate and auto-grades it upon submission."""
    test_instance = get_object_or_404(CandidateTest, secure_id=secure_id)
    
    # SECURITY: If they already took it, block them from taking it again
    if test_instance.is_completed:
        return render(request, 'core/test_already_completed.html')
        
    # --- DYNAMIC QUESTIONS FETCH ---
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