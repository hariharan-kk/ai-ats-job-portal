from django.contrib import admin
from django.utils.html import format_html
from .models import JobPosting, Application, Question, CandidateTest

# Register your JobPosting model
admin.site.register(JobPosting)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'correct_answer')
    search_fields = ('text',) 

@admin.register(CandidateTest)
class CandidateTestAdmin(admin.ModelAdmin):
    list_display = ('application', 'score', 'is_completed', 'completed_at')
    list_filter = ('is_completed',) 
    readonly_fields = ('secure_id', 'score', 'completed_at') 

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    # Notice we added 'view_resume_link' to the end of this list!
    list_display = ('candidate', 'job', 'ai_match_score', 'status', 'applied_at', 'view_resume_link')
    
    list_editable = ('status',) 
    ordering = ('-ai_match_score',)
    list_filter = ('status', 'job', 'applied_at')
    search_fields = ['extracted_text', 'candidate__username']
    
    # --- CUSTOM COLUMN GENERATOR ---
    def view_resume_link(self, obj):
        # Check if the application actually has a file attached
        if obj.resume:
            # Create a clickable HTML button that opens the PDF in a new browser tab
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-weight: bold;">📄 Open PDF</a>', 
                obj.resume.url
            )
        return "No File"
    
    # This sets the column header name in the Django Admin table
    view_resume_link.short_description = "Original Resume"