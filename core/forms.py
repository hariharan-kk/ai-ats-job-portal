from django import forms
from .models import Application
from django.contrib.auth.forms import UserCreationForm
from .models import User

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['resume']
        widgets = {
            'resume': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
        }

class CandidateRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')