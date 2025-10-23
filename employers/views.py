import json, os
import markdown
import openai
import re
import traceback
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import check_password, make_password
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from employers.models import Employer, JobPosting, BlogPost, JobTest, ShortlistedCandidate, CandidateTestResult  #Import models
from candidates.models import Candidate, SkillTestResult
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.contrib.sessions.models import Session
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from bs4 import BeautifulSoup
from html2docx import html2docx
from docx import Document
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

@csrf_exempt
def generate_contracts(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        candidates = data.get("candidates", [])
        if not candidates:
            logger.warning("No candidates provided")
            return JsonResponse({'status': 'error', 'message': 'No candidates provided'}, status=400)

        output_dir = os.path.join(settings.MEDIA_ROOT, 'contracts')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output dir: {output_dir}")

        files = []

        for candidate in candidates:
            text = candidate.get("personalized_text", "").strip()
            if not text:
                logger.warning(f"Missing text for candidate: {candidate}")
                continue

            # Markdown to plain text
            html = markdown.markdown(text)
            plain_text = BeautifulSoup(html, "html.parser").get_text()

            # Create Word doc
            doc = Document()
            for line in plain_text.splitlines():
                doc.add_paragraph(line)

            name = candidate.get("name", "Candidate").replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{name}_{timestamp}.docx"
            filepath = os.path.join(output_dir, filename)

            logger.info(f"Saving file: {filepath}")
            doc.save(filepath)

            file_url = f"{settings.MEDIA_URL}contracts/{filename}"
            files.append(file_url)

        if not files:
            return JsonResponse({'status': 'error', 'message': 'No contracts were generated'}, status=500)

        return JsonResponse({'status': 'success', 'files': files})

    except Exception as e:
        logger.exception("Error generating contracts")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def generate_email(request):
    try:
        data = json.loads(request.body)
        candidates = data.get("candidates", [])
        employer = get_object_or_404(Employer, email=request.user.username)
        prompt = data.get("prompt", "")

        # Construct info string
        candidate_info = "\n".join([
            f"Name: {c.get('name', 'N/A')}, Email: {c.get('email', 'N/A')}, "
            f"Skills: {c.get('skills', 'N/A')}, Address: {c.get('address', 'N/A')}"
            for c in candidates
        ])

        # Full prompt for OpenAI
        full_prompt = (
            f"{prompt}\n\n"
            "Below are sender details\n"
            f"Name: {employer.firstname} {employer.lastname}\n\n"
            f"Company: {employer.company}\n\n"
            f"Email: {employer.email}\n\n"
            f"Phone: {employer.phone}\n\n"
            "If you are writing an job offer email/letter, Format your response like this:\n\n"
            "Subject: <your subject line>\n"
            "Body:\n<your email body>\n\n"
            "Use placeholders [Candidate's Name], [Candidate's Email], [Candidate's Skills] and [Position Title] for candidate, where applicable. For Job details use, [location], [reports_to], [employment_type] and [salary] placeholders. Don't use any other placeholders. Only use given company data.\n If you are generating a contract, create a professional contract document that will be sent by email or email or may be printed. use may use the placeholders as described previously."
        )

        # Send to OpenAI
        
        response = client.chat.completions.create(
            model="gpt-4o",  # or gpt-4, gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are an assistant that writes professional, personalized emails and creates professional contracts between company and candidates."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7,
        )

        # Extract the email content
        email_text = response.choices[0].message.content.strip()

        # Use regex to extract subject and body
        def extract_subject_and_body(text):
            match = re.search(r"Subject:\s*(.*?)\s*Body:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip(), match.group(2).strip()
            else:
                return "Generated Email Subject", text

        subject, body = extract_subject_and_body(email_text)

        return JsonResponse({
            "subject": subject,
            "body": body,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
        
@csrf_exempt
def send_emails(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            email = data.get('email')
            subject = data.get('subject')
            body = data.get('body')  # This should be HTML

            if not all([email, subject, body]):
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

            # Create plain text version from HTML
            text_content = strip_tags(body)

            # Use EmailMultiAlternatives for HTML support
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                'jobsclub458@gmail.com',  # Replace with your sender email
                [email],
            )
            msg.attach_alternative(body, "text/html")  # Attach HTML version
            msg.send()

            return JsonResponse({'status': 'success'})

        except Exception as e:
            print(traceback.format_exc()) 
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'invalid method'}, status=405)



@login_required
def get_shortlisted_candidates(request):
    employer = get_object_or_404(Employer, email=request.user.username)
    
    # Get all shortlisted candidates for this employer
    shortlisted_candidates = ShortlistedCandidate.objects.filter(employer=employer)
    
    candidates = []
    
    for shortlisted in shortlisted_candidates:
        candidate = shortlisted.candidate
        resume = candidate.resume

        
        # Ensures resume is a dictionary and handle accordingly
        if isinstance(resume, str):
            # If resume is a string, attempt to parse it as JSON
            try:
                resume = json.loads(resume)  # Try to parse the string as JSON
            except json.JSONDecodeError:
                resume = {}  # Default to an empty dictionary if parsing fails
        elif not isinstance(resume, dict):
            resume = {}  # Default to an empty dictionary if it's not a string or dict

        # Safely fetch the address from resume if it exists
        address = resume.get('summary', {}).get('Postal Address', 'N/A') if resume else 'N/A'
        
        # Add the candidate details, including the position from ShortlistedCandidate
        if shortlisted.position_id > 0:
            job = get_object_or_404(JobPosting, id=shortlisted.position_id)
            candidates.append({
                'name': f"{candidate.firstname} {candidate.lastname}",
                'email': candidate.email,
                'address': address,
                'skills': candidate.skills,
                'position': shortlisted.position,  
                'position_id':shortlisted.position_id,
                'job_title':job.job_title,
                'location':job.location,
                'employment_type':job.employment_type,
                'reports_to':job.reports_to,
                'salary_range':job.salary_range
            })
            
        else:
            candidates.append({
                'name': f"{candidate.firstname} {candidate.lastname}",
                'email': candidate.email,
                'address': address,
                'skills': candidate.skills,
                'position': shortlisted.position,  
                'position_id':shortlisted.position_id
            })

    # Return candidates as JSON response
    return JsonResponse({'candidates': candidates})


@login_required
def vsearch_candidates(request):
    query = request.GET.get("q", "").strip().lower()
    candidates = []

    if query:
        candidate_queryset = Candidate.objects.filter(
            Q(firstname__icontains=query) |
            Q(lastname__icontains=query) |
            Q(skills__icontains=query)
        )

        # Now check other candidates whose skills are only in the resume
        all_candidates = Candidate.objects.all()
        for candidate in all_candidates:
            try:
                resume_data = candidate.resume
                if isinstance(resume_data, str):
                    resume_data = json.loads(resume_data)
                
                resume_skills = resume_data.get("skills", "")
                address = resume_data.get("summary", {}).get("Postal Address", "N/A")

                # Normalize and check if the query is a skill
                resume_skills_list = [s.strip().lower() for s in resume_skills.split(",") if s.strip()]
                matches_query = (
                    query in candidate.firstname.lower() or
                    query in candidate.lastname.lower() or
                    query in (candidate.skills or "").lower() or
                    query in resume_skills_list
                )
                
                if not matches_query:
                    educations = resume_data.get("educations", [])
                    for edu in educations:
                        for value in edu.values():
                            val = str(value).lower()
                            normalized_query = query.replace(".", "").replace(" ", "")
                            normalized_val = val.replace(".", "").replace(" ", "")
                            
                            
                            if normalized_query in normalized_val:
                                matches_query = True
                                break
                        if matches_query:
                            break

                if matches_query:
                    candidates.append({
                        "name": f"{candidate.firstname} {candidate.lastname}",
                        "skills": resume_skills,
                        "address": address,
                        "email": candidate.email,
                    })

            except (json.JSONDecodeError, TypeError):
                continue

    return JsonResponse(candidates, safe=False)



def job_candidates_view(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id)
    job_skills = [skill.strip().lower() for skill in job.skills.split(",")]

    

    
    # Candidates who attempted the job test
    test_results = CandidateTestResult.objects.filter(job_post=job).select_related(None)
    test_candidates = []

    for result in test_results:
        try:
            candidate = Candidate.objects.get(id=result.candidate_id)
            #candidate_skills = [skill.strip().lower() for skill in candidate.skills.split(",")]
            
            resume_json = json.loads(candidate.resume) if isinstance(candidate.resume, str) else candidate.resume
            resume_skills = resume_json.get('skills', '')
            raw_skills = candidate.skills or resume_skills  # fallback to resume if candidate.skills is empty
            candidate_skills = [s.strip().lower() for s in raw_skills.split(",") if s.strip()]
            skills_data = []

            for skill in candidate_skills:
                skillresult = SkillTestResult.objects.filter(candidate=candidate, skill__iexact=skill).first()

                if skillresult and skillresult.total_marks > 0:
                    percentage = (skillresult.marks / skillresult.total_marks) * 100
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
                
            resume_json = json.loads(candidate.resume) if isinstance(candidate.resume, str) else candidate.resume
            experiences = resume_json.get('experiences', [])
            educations = resume_json.get('educations', [])
            test_candidates.append({
                'id': candidate.id,
                'name': f"{candidate.firstname} {candidate.lastname}",
                'skills': skills_data,
                'experiences': experiences,
                'educations': educations,
                'percentage': round(result.obtained_marks / result.total_marks * 100, 2) if result.total_marks else 0,
                'job_id': job.id,
                'job_title':job.job_title
            })
        except Exception as e:
            print("Error processing test candidate:", e)

    test_candidates.sort(key=lambda c: c['percentage'], reverse=True)

    # Most relevant candidates by skills
    relevant_candidates = []
    all_candidates = Candidate.objects.exclude(id__in=[r.candidate_id for r in test_results])

    for candidate in all_candidates:
        try:
            resume_json = json.loads(candidate.resume) if isinstance(candidate.resume, str) else candidate.resume
            #candidate_skills = [skill.strip().lower() for skill in candidate.skills.split(",")]
            
            resume_json = json.loads(candidate.resume) if isinstance(candidate.resume, str) else candidate.resume
            resume_skills = resume_json.get('skills', '')
            raw_skills = candidate.skills or resume_skills  # fallback to resume if candidate.skills is empty
            candidate_skills = [s.strip().lower() for s in raw_skills.split(",") if s.strip()]


            skills_data = []

            for skill in candidate_skills:
                skillresult = SkillTestResult.objects.filter(candidate=candidate, skill__iexact=skill).first()

                if skillresult and skillresult.total_marks > 0:
                    percentage = (skillresult.marks / skillresult.total_marks) * 100
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
            skill_overlap = set(s.strip() for s in candidate_skills) & set(job_skills)
            matching_skills_data = []

            if not skill_overlap:
                continue
            
            if skill_overlap:
                normalized_job_skills = [s.strip().lower() for s in job_skills]

                skill_tests = SkillTestResult.objects.filter(
                    candidate=candidate,
                )

                # Filter in Python (since Django's __in is case-sensitive for CharField)
                skill_tests = [s for s in skill_tests if s.skill.strip().lower() in normalized_job_skills]
                total = sum(s.total_marks for s in skill_tests)
                obtained = sum(s.marks for s in skill_tests)
                avg_percentage = round(obtained / total * 100, 2) if total else 0
                for s in skill_tests:
                    percentage = round((s.marks / s.total_marks) * 100, 2) if s.total_marks else 0

                    # Assign Bootstrap badge class based on score
                    if percentage >= 80:
                        badge = 'success'
                    elif percentage >= 60:
                        badge = 'warning'
                    else:
                        badge = 'danger'

                    matching_skills_data.append({
                        'skill': s.skill,
                        'badge': badge,
                        'score': percentage
                    })

                relevant_candidates.append({
                    'id': candidate.id,
                    'name': f"{candidate.firstname} {candidate.lastname}",
                    'skills': skills_data,
                    'experiences': resume_json.get('experiences', []),
                    'educations': resume_json.get('educations', []),
                    'percentage': avg_percentage,
                    'job_id': job.id,
                    'job_title':job.job_title,
                    'matched_skills':matching_skills_data,
                    'match_count': len(matching_skills_data)
                })
        except Exception as e:
            print("Error processing skill candidate:", e)

    for c in test_candidates:
        if isinstance(c['skills'], str):
            c['skill_list'] = [s.strip() for s in c['skills'].split(',')]
    for c in relevant_candidates:
        if isinstance(c['skills'], str):
            c['skill_list'] = [s.strip() for s in c['skills'].split(',')]
            
    relevant_candidates.sort(key=lambda c: (c['match_count'], c['percentage']), reverse=True)

    return render(request, 'candidates_modal_content.html', {
        'test_candidates': test_candidates,
        'relevant_candidates': relevant_candidates
    })
    
    
@csrf_exempt
@login_required
def shortlist_candidate(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            candidate_id = int(data.get("candidate_id"))
            position = data.get("position")
            
            if data.get("positionid"):
                positionid = data.get("positionid")
            else:
                positionid = 0

            candidate = Candidate.objects.get(id=candidate_id)
            employer = get_object_or_404(Employer, email=request.user.username)

            ShortlistedCandidate.objects.create(
                candidate=candidate,
                employer=employer,
                position=position,
                position_id=positionid,
                date_shortlisted=timezone.now()
            )

            return JsonResponse({"success": True})

        except Candidate.DoesNotExist:
            return JsonResponse({"success": False, "error": "Candidate not found."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt
def find_candidates(request):
    if request.method == "POST":
        try:
            # Load data from frontend
            data = json.loads(request.body)
            job_description = data.get("description", "")

            # Gather candidate data
            candidates = Candidate.objects.all()
            candidate_info = []

            for candidate in candidates:
                resume_data = candidate.resume

                # Parse resume if it's a string
                if isinstance(resume_data, str):
                    try:
                        resume_data = json.loads(resume_data)
                    except Exception:
                        resume_data = {}

                name = f"{candidate.firstname} {candidate.lastname}"
                skills = candidate.skills or resume_data.get("skills", "")
                experience_list = resume_data.get("experiences", [])

                experience_summary = "; ".join(
                    f"{exp.get('position', '')} at {exp.get('company', '')}"
                    for exp in experience_list
                )

                candidate_info.append({
                    "id": candidate.id,
                    "name": name,
                    "skills": skills,
                    "experience": experience_summary
                })

            # Prepare OpenAI prompt
            prompt = f"""
You are an AI assistant helping an employer find suitable candidates for the following role:
"{job_description}"

Below is a list of candidates with their skills and experience:
{json.dumps(candidate_info, indent=2)}

Based on the job description and candidates' skills and experience, return ONLY the IDs of the most suitable candidates in a JSON format like:
{{"selected_ids": [1, 3, 7]}}
"""

            # Call OpenAI
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert recruiter assistant who only responds in valid JSON."},
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract and clean response
            ai_content = response.choices[0].message.content.strip()
            if ai_content.startswith("```json"):
                ai_content = ai_content[7:-3].strip()
            elif ai_content.startswith("```"):
                ai_content = ai_content[3:-3].strip()

            ai_result = json.loads(ai_content)
            selected_ids = ai_result.get("selected_ids", [])

            # Filter selected candidates
            shortlisted = [c for c in candidate_info if c["id"] in selected_ids]

            return JsonResponse({"success": True, "shortlisted": shortlisted})

        except json.JSONDecodeError as e:
            return JsonResponse({"success": False, "error": "Invalid JSON from OpenAI."}, status=500)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=400)


@csrf_exempt
def save_test(request, job_id):
    """Ensure only one test is saved per job posting."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)  #Parse JSON
            test_questions = data.get("test", [])  #Extract test questions

            if not test_questions:
                return JsonResponse({"success": False, "error": "No test questions provided."}, status=400)

            job = JobPosting.objects.get(id=job_id)

            #Check if a test already exists for this job
            job_test, created = JobTest.objects.get_or_create(job_post=job, defaults={"questions": json.dumps(test_questions), "skills":job.skills})

            if created:  #If new test was created
                message = "Test created successfully."
            else:  #If test already exists, update it
                job_test.questions = json.dumps(test_questions)
                job_test.save()
                message = "Test updated successfully."

            return JsonResponse({"success": True, "message": message})

        except JobPosting.DoesNotExist:
            return JsonResponse({"success": False, "error": "Job not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
            
            



        

def generate_test(request, job_id):
    """ Generate AI-powered test for a job post """
    try:
        #Read the JSON data sent from the frontend
        data = json.loads(request.body)
        num_questions = int(data.get("num_questions", 5))  # Default to 5 if not provided
        job = JobPosting.objects.get(id=job_id)  #Fetch job details

        #Define OpenAI prompt for structured JSON response
        prompt = f"""
        Generate a multiple-choice test for a {job.job_title} role with the following skills: {job.skills}. Divide the questions for each skill equally.
        The test must have {num_questions} questions and must be returned as **valid JSON** in this exact format:
        ```json
        {{
            "questions": [
                {{
                    "question": "What is Python?",
                    "options": ["A. A language", "B. A snake", "C. A car"],
                    "answer": "A. A language"
                }},
                ...
            ]
        }}
        ```
        Ensure the response starts and ends with braces to be a valid JSON object.
        """

        #Make OpenAI API call
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that generates structured multiple-choice tests in JSON format."},
                {"role": "user", "content": prompt}
            ]
        )

        #Extract response & clean JSON format
        raw_response = response.choices[0].message.content.strip()

        #Ensure AI only returns JSON (remove accidental markdown or text artifacts)
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:-3].strip()  # Remove ```json and trailing ```
        elif raw_response.startswith("```"):
            raw_response = raw_response[3:-3].strip()  # Remove ``` and trailing ```

        #Convert string to JSON
        test_json = json.loads(raw_response)  # Convert AI response to JSON format

        return JsonResponse({"success": True, "test": test_json["questions"]})

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON response from OpenAI."}, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


        
        
@login_required
def employer_jobs(request):
    """ Fetch all jobs posted by the employer """
    employer = get_object_or_404(Employer, email=request.user.username)
    jobs = JobPosting.objects.filter(employer=employer).values(
        "id", "job_title", "location", "skills"
    )
    return JsonResponse({"jobs": list(jobs)})

@login_required
def get_blog_posts(request):
    """ Fetch all blog posts for the logged-in employer """
    employer = get_object_or_404(Employer, email=request.user.username)
    blog_posts = BlogPost.objects.filter(employer=employer).values("id", "title", "outline", "content")
    
    return JsonResponse({"posts": list(blog_posts)})

@csrf_exempt
@login_required
def update_blog_post(request, post_id):
    """ Update blog post content """
    blog_post = get_object_or_404(BlogPost, id=post_id, employer__email=request.user.username)
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            blog_post.title = data.get("title", blog_post.title)
            blog_post.outline = data.get("outline", blog_post.outline)
            blog_post.content = data.get("content", blog_post.content)
            blog_post.save()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": f"Update failed: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
@login_required
def delete_blog_post(request, post_id):
    """ Delete a blog post """
    blog_post = get_object_or_404(BlogPost, id=post_id, employer__email=request.user.username)
    blog_post.delete()
    return JsonResponse({"success": True})
    

@csrf_exempt
@login_required
def submit_blog_post(request):
    """ Save the blog outline and post to the database """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            employer = get_object_or_404(Employer, email=request.user.username)

            title = data.get("title", "").strip()
            outline = data.get("outline", "").strip()
            content = data.get("content", "").strip()

            if not title or not content or not outline:
                return JsonResponse({"error": "Title, outline, and content are required."}, status=400)

            BlogPost.objects.create(employer=employer, title=title, outline=outline, content=content)

            return JsonResponse({"success": True, "message": "Blog post saved successfully!"})

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
@login_required
def generate_blog_post(request):
    """ Generate blog outline and full content using AI """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            title = data.get("title", "").strip()

            
            api_key = settings.OPENAI_API_KEY
            client = openai.OpenAI(api_key=api_key)

            #Generate blog outline
            outline_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional blog writer."},
                    {"role": "user", "content": f"Create a structured outline for a blog post titled or a suitable post for job portal if title is not given below: {title}. The outline (only main section headings) should include an introduction, key sections, and a conclusion and should be not more than 200 words in length."}
                ]
            )
            blog_outline = outline_response.choices[0].message.content.strip()
            
            if not title:
                #Generate blog outline
                title_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a professional blog writer."},
                        {"role": "user", "content": f"extract the exact title without changing any word from the outline: {blog_outline}."}
                    ]
                )
                blog_title = title_response.choices[0].message.content.strip()

            #Generate full blog post using the outline
            content_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional blog writer."},
                    {"role": "user", "content": f"Write a detailed blog post based on this outline:\n{blog_outline}.\nKeep the title exact and don't change any word."}
                ]
            )
            blog_content = content_response.choices[0].message.content.strip()
            
            if not title:
                return JsonResponse({"title": blog_title, "outline": blog_outline, "content": blog_content})
            else:
                return JsonResponse({"outline": blog_outline, "content": blog_content})

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def employer_job_posts(request):
    """ Fetch job posts created by the logged-in employer """
    employer = get_object_or_404(Employer, email=request.user.username)
    jobs = JobPosting.objects.filter(employer=employer).values(
        "id", "job_title", "location", "company", "employment_type",
        "experience_level", "reports_to", "salary_range", "application_deadline",
        "skills", "details", "skills"  #Include `details` in response
    )
    return JsonResponse({"jobs": list(jobs)})


@csrf_exempt
@login_required
def update_job_post(request, job_id):
    """ Update a job post """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            job = get_object_or_404(JobPosting, id=job_id, employer__email=request.user.username)

            job.job_title = data.get("job_title", job.job_title)
            job.location = data.get("location", job.location)
            job.company = data.get("company", job.company)
            job.employment_type = data.get("employment_type", job.employment_type)
            job.experience_level = data.get("experience_level", job.experience_level)
            job.reports_to = data.get("reports_to", job.reports_to)
            job.salary_range = data.get("salary_range", job.salary_range)
            job.application_deadline = data.get("application_deadline", job.application_deadline)
            job.skills = data.get("skills", job.skills)
            job.details = data.get("details", job.details)
            job.save()

            return JsonResponse({"success": True, "message": "Job updated successfully!"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})

@csrf_exempt
@login_required
def delete_job_post(request, job_id):
    """ Delete a job post """
    try:
        job = get_object_or_404(JobPosting, id=job_id, employer__email=request.user.username)
        job.delete()
        return JsonResponse({"success": True, "message": "Job deleted successfully!"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
    
    
@login_required
def employer_dashboard(request):
    #Ensure session is active
    session_key = request.session.session_key
    if not session_key:
        request.session.create()  #Initialize session if missing
    return render(request, "employerspanel.html", {"user": request.user})

@login_required
def job_posting(request):
    if request.method == "POST":
        try:
            employer = Employer.objects.get(email=request.user.username)  #Get logged-in employer

            job = JobPosting.objects.create(
                employer=employer,
                job_title=request.POST.get("job_title"),
                location=request.POST.get("location"),
                company=request.POST.get("company"),
                employment_type=request.POST.get("employment_type"),
                experience_level=request.POST.get("experience_level"),
                reports_to=request.POST.get("reports_to"),
                salary_range=request.POST.get("salary_range"),
                application_deadline=request.POST.get("application_deadline"),
                skills=request.POST.get("skills"),
                details=request.POST.get("job_details_post")
            )

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})
    
    

def home(request):
    return render(request, 'home.html')
    
def employer_register(request):
    if request.method == "POST":
        firstname = request.POST.get("firstname")
        lastname = request.POST.get("lastname")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        company = request.POST.get("company")
        phone = request.POST.get("phone")
        joined_date = request.POST.get("joined_date")

        #Validate mandatory fields
        if not firstname or not lastname or not email or not password or not confirm_password or not company:
            messages.error(request, "All fields except Phone and Joined Date are required.")
            return redirect("employer_register")

        #Validate password length
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect("employer_register")

        #Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("employer_register")

        #Check if email already exists
        if Employer.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect("employer_register")

        #Hash password before saving
        hashed_password = make_password(password)

        #Create new employer record
        employer = Employer(
            firstname=firstname,
            lastname=lastname,
            email=email,
            password=hashed_password,
            company=company,
            phone=phone if phone else None,
            joined_date=joined_date if joined_date else None,
        )
        employer.save()

        messages.success(request, "Registration successful! You can now log in.")
        return redirect("employer_login")

    return render(request, "register.html")
    
def employer_login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        try:
            employer = Employer.objects.get(email=email)  #Check if employer exists
            if check_password(password, employer.password):  #Validate password
                
                #Ensure Django User exists
                user, created = User.objects.get_or_create(username=employer.email)  
                login(request, user)  #Django recognizes user session now

                #Store employer details in session
                request.session["employer_id"] = employer.id  
                request.session["employer_email"] = employer.email  
                request.session.modified = True  #Ensure session updates

                return redirect("employer_dashboard")  #Redirect to dashboard
            else:
                messages.error(request, "Invalid email or password")
        except Employer.DoesNotExist:
            messages.error(request, "Invalid email or password")

    return render(request, "login.html")  #Show login page



def post_vacancy(request):
    return render(request, "employers/post_vacancy.html")

def generate_contract(request):
    return render(request, "employers/generate_contract.html")

def create_job_vacancy(request):
    return render(request, "employers/create_job_vacancy.html")
        
@csrf_exempt  #Disable CSRF for testing (ensure CSRF is handled in production)
def generate_job_post(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_input = data.get("job_description", "")

            if not user_input.strip():
                return JsonResponse({"error": "Please enter job details before generating."}, status=400)

            api_key = settings.OPENAI_API_KEY
            if not api_key:
                return JsonResponse({"error": "OpenAI API key is missing."}, status=400)

            client = openai.OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional job posting generator."},
                    {"role": "user", "content": f"Improve this job post or create a new one if only short details are given: {user_input}. Ensure the generated post includes summary a summary in start before actual post that must include:\n\n- Job Title\n- Location\n- Company\n- Employment Type\n- Experience Level\n- Reports to\n- Salary Range / month\n- Application Deadline\n- Required Skills\n-"}
                ]
            )

            job_posting = response.choices[0].message.content.strip()

            return JsonResponse({"job_posting": job_posting})

        except openai.OpenAIError as e:
            return JsonResponse({"error": f"OpenAI API Error: {str(e)}"}, status=500)

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)
            


def create_email(request):
    return render(request, "employers/create_email.html")

def shortlist_candidates(request):
    return render(request, "employers/shortlist_candidates.html")

def create_order(request):
    return render(request, "employers/create_order.html")

def recommend_candidates(request):
    return render(request, "employers/recommend_candidates.html")

def generate_tests(request):
    return render(request, "employers/generate_tests.html")

    
def employer_logout(request):
    request.session.flush()  # Clear session data
    return redirect("employer_login")  # Redirect to login page
    
