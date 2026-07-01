from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

# --- ADD THESE TWO IMPORTS ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('apply/<int:job_id>/', views.apply_for_job, name='apply_for_job'),
    path('dashboard/', views.candidate_dashboard, name='dashboard'),
    path('hr/', views.custom_hr_dashboard, name='hr_dashboard'),
    path('hr/application/<int:app_id>/', views.hr_application_detail, name='hr_application_detail'),
    path('hr/jobs/add/', views.add_job_posting, name='add_job_posting'),
    
    # Secure test link
    path('test/<uuid:secure_id>/', views.take_aptitude_test, name='take_aptitude_test'),

    path('register/', views.register_candidate, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='job_list'), name='logout'),
]

# --- ADD THIS BLOCK TO THE VERY BOTTOM ---
# This allows HR to actually view and download the uploaded PDF resumes
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)