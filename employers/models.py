from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils.timezone import now
from django.utils import timezone

class JobTest(models.Model):
    job_post = models.ForeignKey("JobPosting", on_delete=models.CASCADE)  # Link to Job
    skills = models.TextField()  #Store skills
    questions = models.JSONField()  #Store Questions & Options as JSON
    created_at = models.DateTimeField(default=now)  #Auto timestamp

    def __str__(self):
        return f"Test for {self.job_post.job_title}"
        
        

class BlogPost(models.Model):
    employer = models.ForeignKey("Employer", on_delete=models.CASCADE)  #Link to employer
    title = models.CharField(max_length=255)
    approved = models.CharField(max_length=50, default='no')
    outline = models.TextField()  #Store AI-generated outline
    content = models.TextField()
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return self.title
        
        
class Employer(models.Model):
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)  # Store the hashed password
    active = models.CharField(max_length=50, default='yes')
    company = models.CharField(max_length=255)
    phone = models.IntegerField(null=True)
    joined_date = models.DateField(null=True)

    def save(self, *args, **kwargs):
        # Hash the password before saving
        if not self.password.startswith('pbkdf2_sha256$'):  # Avoid double hashing
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
        
class JobPosting(models.Model):
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)  #Link Job to Employer
    job_title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=50)
    experience_level = models.CharField(max_length=50)
    approved = models.CharField(max_length=50, default='no')
    reports_to = models.CharField(max_length=255)
    salary_range = models.CharField(max_length=255)
    application_deadline = models.DateField()
    skills = models.TextField()
    details = models.TextField()
    posting_date = models.DateField(default=now)  #Auto-set posting date

    def __str__(self):
        return self.job_title


class CandidateTestResult(models.Model):
    candidate_id = models.IntegerField()
    job_post = models.ForeignKey(JobPosting, on_delete=models.CASCADE)
    answers = models.JSONField()
    obtained_marks = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(default=now)
    
    
class ShortlistedCandidate(models.Model):
    candidate = models.ForeignKey('candidates.Candidate', on_delete=models.CASCADE)
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)
    position = models.CharField(max_length=255)
    position_id = models.IntegerField(default=0)
    date_shortlisted = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.candidate.firstname} shortlisted by {self.employer.id} for {self.position}"