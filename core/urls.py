from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('apply/<int:job_id>/', views.apply_for_job, name='apply_for_job'),
    path('dashboard/', views.candidate_dashboard, name='dashboard'),

    path('register/', views.register_candidate, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='job_list'), name='logout'),
]