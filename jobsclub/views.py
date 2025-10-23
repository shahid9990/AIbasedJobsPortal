from django.shortcuts import render, redirect, get_object_or_404
import markdown
from employers.models import JobPosting, BlogPost  #Import models
from candidates.models import Candidate, SkillTestResult
import json
def candidate_profile_v(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    resume_data = candidate.resume or {}
    if isinstance(resume_data, str):
        try:
            resume_data = json.loads(resume_data)
        except json.JSONDecodeError:
            resume_data = {}

    test_results = SkillTestResult.objects.filter(candidate=candidate)
    
    return render(request, 'cprofile.html', {
        'candidate': candidate,
        'resume': resume_data,
        'test_results': test_results
    })


def home(request):
    """ Fetch approved job posts and blog posts for the home page """
    job_posts = JobPosting.objects.filter(approved="yes").order_by("-posting_date")[:6]  #Get latest 5 jobs
    blog_posts = BlogPost.objects.filter(approved="yes").order_by("-created_at")[:5]  #Get latest 5 blogs

    return render(request, "home.html", {"job_posts": job_posts, "blog_posts": blog_posts})

def job_details(request, job_id):
    """ Display full job posting details with Markdown converted to HTML """
    job = get_object_or_404(JobPosting, id=job_id, approved="yes")
    
    job.details = markdown.markdown(job.details)  #Convert Markdown to HTML

    return render(request, "job_details.html", {"job": job})

def blog_details(request, blog_id):
    """ Display full blog post details with Markdown converted to HTML """
    blog = get_object_or_404(BlogPost, id=blog_id, approved="yes")
    
    
    blog.content = markdown.markdown(blog.content)  #Convert Markdown to HTML

    return render(request, "blog_details.html", {"blog": blog})