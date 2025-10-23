from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password


class Candidate(models.Model):
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  
    phone = models.CharField(max_length=15, blank=True, null=True)
    resume = models.JSONField(default=dict, blank=True, null=True)
    skills = models.TextField(null=True)
    joined_date = models.DateTimeField(auto_now_add=True)
    selected_theme = models.CharField(max_length=50, default="default")

    def save(self, *args, **kwargs):
        if not self.password.startswith("pbkdf2_sha256$"):  #Avoid re-hashing an already hashed password
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firstname} {self.lastname}"
        


class SkillTestResult(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    skill = models.CharField(max_length=200)
    marks = models.FloatField()
    total_marks = models.FloatField()
    taken_at = models.DateTimeField(auto_now_add=True)
