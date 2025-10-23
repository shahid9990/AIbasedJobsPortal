from django.contrib import admin
from .models import Candidate, SkillTestResult

# Register your models here.
admin.site.register(Candidate)
admin.site.register(SkillTestResult)