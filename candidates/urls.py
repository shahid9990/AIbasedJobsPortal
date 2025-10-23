from django.urls import path

from .views import candidate_register, candidate_login, candidate_dashboard, CandidatePasswordResetView, candidate_logout, candidate_profile, update_candidate_profile, change_candidate_password, candidate_password, resume_builder, generate_resume, save_resume, get_blog_posts, get_job_posts, view_blog_post, view_job_post, get_test, submit_test, candidate_skillsset, generate_skill_test, submit_skill_test
from django.contrib.auth.views import (
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)

urlpatterns = [
    path("register/", candidate_register, name="candidate_register"),
    path("login/", candidate_login, name="candidate_login"),
    path("dashboard/", candidate_dashboard, name="candidate_dashboard"),
    path("password-reset/", CandidatePasswordResetView.as_view(), name="candidate_password_reset"),
    path("password-reset/done/", PasswordResetDoneView.as_view(template_name="candidates/password_reset_done.html"), name="candidate_password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", PasswordResetConfirmView.as_view(template_name="candidates/password_reset_confirm.html"), name="candidate_password_reset_confirm"),
    path("password-reset-complete/", PasswordResetCompleteView.as_view(template_name="candidates/password_reset_complete.html"), name="candidate_password_reset_complete"),
    path("logout/", candidate_logout, name="candidate_logout"),
    path("profile/", candidate_profile, name="candidate_profile"),
    path("profile/update/", update_candidate_profile, name="update_candidate_profile"),
    path("password/", candidate_password, name="candidate_password"),
    path("profile/change-password/", change_candidate_password, name="change_candidate_password"),
    path("resume-builder/", resume_builder, name="resume_builder"),
    path("generate-resume/", generate_resume, name="generate_resume"),
    path("save-resume/", save_resume, name="save_resume"),
    path("blog-posts/", get_blog_posts, name="get_blog_posts"),
    path("job-posts/", get_job_posts, name="get_job_posts"),
    path("view-blog/<int:post_id>/", view_blog_post, name="view_blog_post"),
    path("view-job/<int:job_id>/", view_job_post, name="view_job_post"),
    path('get-test/<int:job_id>/', get_test, name='get_test'),
    path('submit-test/', submit_test, name='submit_test'),
    path('get-candidate-skills/', candidate_skillsset, name='candidate_skillsset'),
    path('generate-skill-test/', generate_skill_test, name='generate_skill_test'),
    path('submit-skill-test/', submit_skill_test, name='submit_skill_test'),
]
