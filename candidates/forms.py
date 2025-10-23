from django import forms
from .models import Candidate
from django.contrib.auth.hashers import make_password

class CandidateRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = Candidate
        fields = ["firstname", "lastname", "email", "password", "phone", "resume"]

    def save(self, commit=True):
        candidate = super().save(commit=False)
        candidate.password = make_password(self.cleaned_data["password"])  #Hash password
        if commit:
            candidate.save()
        return candidate

class CandidateLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
