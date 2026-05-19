from django.contrib import admin
from .models import JobPosting, Application

# Register your JobPosting model (so you can add jobs!)
admin.site.register(JobPosting)

# Register your newly upgraded Application model
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'ai_match_score', 'status', 'applied_at')
    list_editable = ('status',) 
    list_filter = ('status', 'job', 'applied_at')
    ordering = ('-ai_match_score',)

admin.site.register(Application, ApplicationAdmin)