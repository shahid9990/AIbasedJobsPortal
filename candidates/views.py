import json
import openai
from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .decorators import candidate_required
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import check_password
from django.contrib.auth.views import PasswordResetView
from django.conf import settings
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Candidate, SkillTestResult
from employers.models import BlogPost, JobPosting, JobTest, CandidateTestResult
from .forms import CandidateRegistrationForm, CandidateLoginForm
from django import forms
from django.contrib.auth.hashers import make_password
from django.views.decorators.http import require_http_methods
from django.db.models import Q


@candidate_required
def generate_skill_test(request):
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    skill = request.GET.get('skill')
    if not skill:
        return JsonResponse({'success': False, 'message': 'Skill not provided'})

    prompt = f"""
    Generate 20 multiple choice questions (MCQs) for assessing knowledge of {skill}.
    Each question should have exactly 4 options. Remember that if a question includes some html code or tags, it should be included so that we can make it part of html paragraphs or options without disturbing the whole output.
    Format as JSON with structure:
    [
      {{
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "answer": "A"
      }},
      ...
    ]
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()
        questions = json.loads(content)
        return JsonResponse({'success': True, 'questions': questions})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@csrf_exempt
@candidate_required
def submit_skill_test(request):
    try:
        candidate_id = request.session.get("candidate_id")
        candidate = Candidate.objects.get(id=candidate_id)

        data = json.loads(request.body)
        skill = data.get("skill")
        answers = data.get("answers")

        if not skill or not answers:
            return JsonResponse({"success": False, "message": "Missing skill or answers."}, status=400)

        # Calculate marks
        score = 0
        total = len(answers)

        for ans in answers:
            if ans.get("selected", "").strip() == ans.get("answer", "").strip():
                score += 1

        # Check for existing result
        result, created = SkillTestResult.objects.update_or_create(
            candidate=candidate,
            skill=skill,
            defaults={
                'marks': score,
                'total_marks': total
            }
        )

        return JsonResponse({
            "success": True,
            "message": f"Test submitted. Score: {score}/{total}",
            "score": score,
            "total": total
        })

    except Candidate.DoesNotExist:
        return JsonResponse({"success": False, "message": "Candidate not found."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"}, status=500)




def candidate_skillsset(request):
    candidate_id = request.session.get("candidate_id")
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidate not be found.'}, status=404)

    # Step 1: Try to get skills from the 'skills' field
    skills_raw = candidate.skills

    if not skills_raw or not skills_raw.strip():
        # Step 2: If empty, try to get skills from resume JSON
        resume_data = candidate.resume or {}
        if isinstance(resume_data, str):
            try:
                resume_data = json.loads(resume_data)
            except json.JSONDecodeError:
                resume_data = {}

        skills_raw = resume_data.get('skills', "")

    # Normalize and split skills
    skills = [skill.strip() for skill in skills_raw.split(",") if skill.strip()]
    skills_data = []

    for skill in skills:
        result = SkillTestResult.objects.filter(candidate=candidate, skill__iexact=skill).first()

        if result and result.total_marks > 0:
            percentage = (result.marks / result.total_marks) * 100
            if percentage >= 70:
                badge = 'success'
            elif 50 <= percentage < 70:
                badge = 'warning'
            else:
                badge = 'danger'
        else:
            badge = 'danger'
            percentage = 0

        skills_data.append({
            'skill': skill,
            'badge': badge,
            'score': percentage
        })

    return JsonResponse({'success': True, 'skills': skills_data})


def view_job_post(request, job_id):
    try:
        job = JobPosting.objects.get(pk=job_id)
        test_exists = JobTest.objects.filter(job_post_id=job_id).exists()

        response_data = {
            'success': True,
            'job_post': {
                'job_title': job.job_title,
                'location': job.location,
                'company': job.company,
                'employment_type': job.employment_type,
                'experience_level': job.experience_level,
                'reports_to': job.reports_to,
                'salary_range': job.salary_range,
                'application_deadline': job.application_deadline.strftime('%Y-%m-%d'),
                'skills': job.skills,
                'details': job.details,
            },
            'test_exists': test_exists  # this should now appear
        }

     

        return JsonResponse(response_data)

    except JobPosting.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Job not found'})


@csrf_exempt
@candidate_required
def get_test(request, job_id):
    try:
        candidate_id = request.session.get("candidate_id")
        candidate = Candidate.objects.get(id=candidate_id)

        job = JobPosting.objects.get(pk=job_id)
        test = JobTest.objects.get(job_post_id=job_id)

        # ✅ Check if candidate already attempted the test
        already_attempted = CandidateTestResult.objects.filter(
            candidate_id=candidate.id, job_post_id=job_id
        ).exists()

        if already_attempted:
            return JsonResponse({
                'success': False,
                'message': 'You have already attempted this test.'
            }, status=403)

        return JsonResponse({
            'success': True,
            'questions': test.questions
        })

    except JobPosting.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Job not found.'}, status=404)
    except JobTest.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Test not available.'}, status=404)
    except Candidate.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Candidate not found.'}, status=403)


@csrf_exempt
@candidate_required
def submit_test(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    try:
        candidate_id = request.session.get("candidate_id")
        candidate = Candidate.objects.get(id=candidate_id)

        data = json.loads(request.body)
        job_id = data.get('job_id')
        answers = data.get('answers')

        if not job_id or not answers:
            return JsonResponse({'success': False, 'message': 'Missing job ID or answers.'}, status=400)

        try:
            job = JobPosting.objects.get(id=job_id)
        except JobPosting.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid job ID.'}, status=404)

        try:
            generated_test = JobTest.objects.get(job_post=job)
        except JobTest.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No test found for this job.'}, status=404)

        # Restrict to one attempt
        already_attempted = CandidateTestResult.objects.filter(candidate_id=candidate.id, job_post=job).exists()
        if already_attempted:
            return JsonResponse({'success': False, 'message': 'You have already attempted this test.'}, status=403)

        correct_questions = json.loads(generated_test.questions)
        correct_answers = {q['question']: q['answer'] for q in correct_questions}

        score = 0
        total = len(correct_questions)

        for ans in answers:
            q = ans['question']
            selected = ans['selected']
            if q in correct_answers and selected.strip() == correct_answers[q].strip():
                score += 1

        # Save result
        CandidateTestResult.objects.create(
            candidate_id=candidate.id,
            job_post=job,
            answers=json.dumps(answers),
            obtained_marks=score,
            total_marks=total
        )

        return JsonResponse({
            'success': True,
            'message': f'Test submitted successfully! You scored {score}/{total}.',
            'score': score,
            'total': total
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Server error: {str(e)}'}, status=500)

    
    

def get_blog_posts(request):
    """ Fetch all blog posts for candidates """
    blog_posts = BlogPost.objects.values("id", "title", "outline").filter(approved="yes")
    return JsonResponse({"success": True, "blog_posts": list(blog_posts)})

def get_job_posts(request):
    """ Fetch all job postings for candidates """
    job_posts = JobPosting.objects.values("id", "job_title", "location", "skills", "company", "application_deadline")
    return JsonResponse({"success": True, "job_posts": list(job_posts)})

def view_blog_post(request, post_id):
    """ Fetch full blog post """
    blog_post = get_object_or_404(BlogPost, id=post_id)
    return JsonResponse({"success": True, "title": blog_post.title, "content": blog_post.content})



def resume_builder(request):
    """ Fetch resume from database and return as valid JSON """
    if request.method == "GET" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        try:
            candidate = Candidate.objects.get(id=request.session["candidate_id"])
            
            #Decode JSON string from database
            resume_json = json.loads(candidate.resume) if candidate.resume else {}

            return JsonResponse({"success": True, "resume": resume_json})

        except Candidate.DoesNotExist:
            return JsonResponse({"success": False, "error": "Candidate not found."}, status=404)

    return render(request, "candidates/resume_builder.html")

def generate_resume(request):
    """ Generate AI-powered resume """
    try:
        data = json.loads(request.body)  #Read input data

        prompt = f"""
        Generate a professional resume in JSON format.
        Candidate Summary: {data.get('summary', 'N/A')}
        Work Experience: {data.get('experiences', 'N/A')}
        Education: {data.get('educations', 'N/A')}
        Skills: {data.get('skills', 'N/A')} remove extra text if any only skills are needed
        Languages: {data.get('languages', 'N/A')}
        The resume must be JSON structured as follows:
        ```json
        {{
            "name": "{data.get('firstname', '')} {data.get('lastname', '')}",
            "summary": "...",
            "experiences": [...],
            "educations": [...],
            "skills": "...",
            "languages": "...",
            "theme": "{data.get('theme', 'classic')}"
        }}
        ```
        Ensure the response starts with '{{' and ends with '}}' to be valid JSON and structure such it is easily render using the following javascript function:
        function renderResume(resume) {{
    let preview = `<h3>${{resume.name || "N/A"}}</h3>`;

    //Handle summary (handles both string and object formats)
    if (typeof resume.summary === "string") {{
        preview += `<p><strong>Summary:</strong> ${{resume.summary}}</p>`;
    }} else if (typeof resume.summary === "object") {{
        preview += `<h4>Summary</h4><ul>`;
        Object.entries(resume.summary).forEach(([key, value]) => {{
            preview += `<li><strong>${{formatKey(key)}}:</strong> ${{value}}</li>`;
        }});
        preview += `</ul>`;
    }}

    //Handle experience
    if (Array.isArray(resume.experiences) && resume.experiences.length > 0) {{
        preview += `<h4>Experience</h4><ul>`;
        resume.experiences.forEach(exp => {{
            preview += `<li><strong>${{exp.position || "N/A"}}</strong> at ${{exp.company || "N/A"}} 
                        (${{exp.startDate || "N/A"}} - ${{exp.endDate || "N/A"}}) 
                        <br><em>${{exp.location || "N/A"}}</em>`;
            if (exp.description) preview += `<br>${{exp.description}}`;
            preview += `</li>`;
        }});
        preview += `</ul>`;
    }}

    //Handle education
    if (Array.isArray(resume.educations) && resume.educations.length > 0) {{
        preview += `<h4>Education</h4><ul>`;
        resume.educations.forEach(edu => {{
            preview += `<li><strong>${{edu.degree || "N/A"}}</strong> at ${{edu.institution || "N/A"}} 
                        (${{edu.date || "N/A"}})`;
            if (edu.grade) preview += ` - Grade: ${{edu.grade}}`;
            if (edu.subjects) preview += ` - Subjects: ${{edu.subjects}}`;
            preview += `</li>`;
        }});
        preview += `</ul>`;
    }}

    //Handle skills
    if (resume.skills) {{
        preview += `<p><strong>Skills:</strong> ${{resume.skills}}</p>`;
    }}

    //Handle languages
    if (resume.languages) {{
        preview += `<p><strong>Languages:</strong> ${{resume.languages}}</p>`;
    }}
        """

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You generate structured JSON resumes."},
                {"role": "user", "content": prompt}
            ]
        )

        #Extract OpenAI response
        raw_response = response.choices[0].message.content.strip()

        #Ensure AI response contains valid JSON only
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:-3].strip()  # Remove markdown block
        elif raw_response.startswith("```"):
            raw_response = raw_response[3:-3].strip()

        #Convert AI response to JSON
        resume_json = json.loads(raw_response)

        #Ensure required fields exist
        resume_json.setdefault("name", "N/A")
        resume_json.setdefault("summary", "N/A")
        resume_json.setdefault("experiences", [])
        resume_json.setdefault("educations", [])
        resume_json.setdefault("skills", "N/A")
        resume_json.setdefault("languages", "N/A")
        resume_json.setdefault("theme", data.get("theme", "classic"))

        return JsonResponse({"success": True, "resume": resume_json})

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON response from OpenAI."}, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

def save_resume(request):
    candidate = Candidate.objects.get(id=request.session["candidate_id"])
    data = json.loads(request.body)
    candidate.resume = json.dumps(data["resume"])
    candidate.save()
    return JsonResponse({"message": "Resume saved successfully!"})


    
@candidate_required
def candidate_password(request):
    """ Display Candidate Profile """
    candidate = Candidate.objects.get(id=request.session["candidate_id"])
    return render(request, "candidates/candidate_password.html", {"candidate": candidate})

@candidate_required
def change_candidate_password(request):
    """ Change candidate password """
    if request.method == "POST":
        candidate_id = request.session.get("candidate_id")
        if not candidate_id:
            return JsonResponse({"success": False, "error": "Unauthorized. Please log in."}, status=403)

        candidate = Candidate.objects.get(id=candidate_id)
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validate old password
        if not check_password(old_password, candidate.password):
            return JsonResponse({"success": False, "error": "Incorrect old password."})

        # Validate new password match
        if new_password != confirm_password:
            return JsonResponse({"success": False, "error": "New passwords do not match."})

        # Update password
        candidate.password = make_password(new_password)
        candidate.save()

        return JsonResponse({"success": True, "message": "Password updated successfully!"})

    return JsonResponse({"success": False, "error": "Invalid request."})


@candidate_required
def candidate_profile(request):
    """ Display Candidate Profile """
    candidate = Candidate.objects.get(id=request.session["candidate_id"])
    return render(request, "candidates/profile.html", {"candidate": candidate})

@candidate_required
def update_candidate_profile(request):
    """ Update candidate profile """
    try:
        candidate = Candidate.objects.get(id=request.session["candidate_id"])  #Get logged-in candidate

        if request.method == "POST":
            candidate.firstname = request.POST.get("firstname", candidate.firstname)
            candidate.lastname = request.POST.get("lastname", candidate.lastname)
            candidate.phone = request.POST.get("phone", candidate.phone)
            candidate.save()

            return JsonResponse({"success": True, "message": "Profile updated successfully!"})

    except Candidate.DoesNotExist:
        return JsonResponse({"success": False, "error": "Candidate not found."})

    return JsonResponse({"success": False, "error": "Invalid request."})

def candidate_register(request):
    if request.method == "POST":
        firstname = request.POST.get("firstname").strip()
        lastname = request.POST.get("lastname").strip()
        email = request.POST.get("email").strip()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        phone = request.POST.get("phone").strip()

        # Basic Validations
        if not firstname or not lastname or not email or not password or not confirm_password:
            messages.error(request, "All fields are required except phone.")
            return redirect("candidate_register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("candidate_register")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect("candidate_register")

        # Check if candidate already exists
        if Candidate.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered. Try logging in.")
            return redirect("candidate_register")

        #Save candidate
        candidate = Candidate(
            firstname=firstname,
            lastname=lastname,
            email=email,
            password=make_password(password),  #Secure Password
            phone=phone if phone else None,
        )
        candidate.save()

        messages.success(request, "Registration successful! You can now log in.")
        return redirect("candidate_login")

    return render(request, "candidates/register.html")
    


def candidate_login(request):
    """ Handle candidate login """
    if request.method == "POST":
        form = CandidateLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                candidate = Candidate.objects.get(email=email)
                if check_password(password, candidate.password):  #Validate password
                    request.session["candidate_id"] = candidate.id
                    request.session["candidate_email"] = candidate.email
                    return redirect("candidate_dashboard")  #Redirect to dashboard
                else:
                    messages.error(request, "Invalid email or password")
            except Candidate.DoesNotExist:
                messages.error(request, "Invalid email or password")
    else:
        form = CandidateLoginForm()
    return render(request, "candidates/login.html", {"form": form})

@candidate_required
def candidate_dashboard(request):
    """ Display Candidate Dashboard """
    candidate = Candidate.objects.get(id=request.session["candidate_id"])
    return render(request, "candidates/dashboard.html", {"candidate": candidate})
    
class CandidatePasswordResetView(PasswordResetView):
    template_name = "candidates/password_reset.html"  #Custom template
    email_template_name = "candidates/password_reset_email.html"  #Custom email template
    success_url = reverse_lazy("candidates:password_reset_done")
    subject_template_name = "candidates/password_reset_subject.txt"
    
    def get_users(self, email):
        """Override get_users to use the Candidate model instead of Django's User model."""
        UserModel = get_user_model()
        return UserModel.objects.filter(email=email)
        
        
def candidate_logout(request):
    request.session.flush()  #Clear session
    return redirect("candidate_login")
