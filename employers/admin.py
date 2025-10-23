from django.contrib import admin
from .models import Employer, JobPosting, BlogPost, JobTest, CandidateTestResult, ShortlistedCandidate

# Register your models here.
admin.site.register(Employer)
admin.site.register(JobPosting)
admin.site.register(BlogPost)
admin.site.register(JobTest)
admin.site.register(CandidateTestResult)
admin.site.register(ShortlistedCandidate)