from django.contrib import admin
from .models import JobPosting, Application
from .models import Question, CandidateTest

# Register your JobPosting model (so you can add jobs!)
admin.site.register(JobPosting)

# Register your newly upgraded Application model
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'ai_match_score', 'status', 'applied_at')
    list_editable = ('status',) 
    list_filter = ('status', 'job', 'applied_at')
    ordering = ('-ai_match_score',)
    search_fields = ('name', 'email', 'extracted_text')

admin.site.register(Application, ApplicationAdmin)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'correct_answer')
    search_fields = ('text',) # Let HR search for specific questions

@admin.register(CandidateTest)
class CandidateTestAdmin(admin.ModelAdmin):
    list_display = ('application', 'score', 'is_completed', 'completed_at')
    list_filter = ('is_completed',) # Let HR filter to see who hasn't taken the test yet
    readonly_fields = ('secure_id', 'score', 'completed_at') # Prevent HR from accidentally changing scores