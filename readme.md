The Jobs Club and AI Recruitment & staffing Web Application will revolutionize the recruitment industry/HR departments by using the AI-powered tools to create a user-friendly platform. In this system the staffing agency operations are streamlined. These operations include employer, candidate, tests, postings and order management. It also manages the placements, automated content generation, tests, test results management, automated email generation, and contracts generation that are exported to word format. The efficiency of the system is enhanced by using GPT models from OpenAI while ensuring compliance with agency policies. The system provide unparalleled support for employers, candidates and administrators. This Web Application have a deep integration with OpenAI’s GPT models. 

Tools:
Python, Django, CSS, HTML, JQuery, AJAX

Functionalities:
This app fulfills the following purposes:

i.	Candidate Recommendations: 
Employers and Admins can now find the best candidates for a given role using the power of AI. Our Candidate Recommendation feature is a powerful tool that will change the way you recruit forever!

ii.	Candidate Bio filter: 
our candidate bio filter drastically reduces the manpower needs of your agency. You can configure the AI model to filter each candidate’s bio to remove any text that violates your terms of service.

iii.	Employer Job Vacancy filter: 
Our job vacancy filter ensures that each time an employer creates a job vacancy, it comply's with your policies. You can even have the Gpt model automatically re-write each job posting to enforce quality standards.

iv.	Contract Generation: 
Automatically create contracts with the AI contract generation feature. The system will use the signatories you have configured to draft a professional legal document.

v.	Candidate Bio Generator: 
Easily create professional bios for your candidates with the click of a button. The system will gather all the candidate’s data and draft a professional bio.

vi.	Job vacancy generator: 
Employers and admins can use AI to easily create professional job listings automatically.

vii.	Blog post generator: 
Easily create blog posts with the built-in AI-based blog post generator.

viii.	Email creation: 
Save time drafting emails with the built-in email template creator

ix.	Roles Supported: 
3 roles supported a) Candidate b) Employer c) Administrator

x.	Vacancies posting on Portal: 
Easily post vacancies on your portal. Receive applications for each vacancy from your candidates. Download resumes for each applicant. This app also provides powerful filtering features for selecting the right candidates for each position.

xi.	Employers can optionally shortlist candidates while placing orders. 
You get to define candidates that are available for shortlisting on your front end. You can also create orders from your backend and shortlist candidates yourself.

How to use it:
1. Download the code files.
2. Go to jobsclub/settings.py.
3. Scroll the the line where it says OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "PUT Your OpenAI API key here"), just put the openai key where it says PUT Your OpenAI API key here.
4. setup the email account at the end of this file. If you are using gmail account, you will have to set it up for smtp.

Future Enhancements:
1. Integration of models from openrouter/bedrock/others.
2. Integration of self hosted models where own GPU will be used.
