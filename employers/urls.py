from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from .views import employer_login, employer_dashboard, generate_contract, create_job_vacancy, generate_blog_post, create_email, shortlist_candidates, create_order, recommend_candidates, employer_logout, generate_job_post, employer_register, employer_job_posts, job_posting, update_job_post, delete_job_post, submit_blog_post, get_blog_posts, update_blog_post, delete_blog_post, generate_test, save_test, employer_jobs, find_candidates, shortlist_candidate, job_candidates_view, get_shortlisted_candidates, vsearch_candidates, generate_email, send_emails, generate_contracts

urlpatterns = [
    path("login/", employer_login, name="employer_login"),
    path("register/", employer_register, name="employer_register"),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="password_reset.html"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="password_reset_confirm.html"), name="password_reset_confirm"),
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"), name="password_reset_complete"),
    path("dashboard/", employer_dashboard, name="employer_dashboard"),
    path("job-posts/", employer_job_posts, name="employer_job_posts"),
    path("post-job/", job_posting, name="job_posting"),
    path("update-job/<int:job_id>/", update_job_post, name="update_job_post"),
    path("delete-job/<int:job_id>/", delete_job_post, name="delete_job_post"),
    path("generate-contract/", generate_contract, name="generate_contract"),
    path("create-job-vacancy/", create_job_vacancy, name="create_job_vacancy"),
    path('generate-job-post/', generate_job_post, name='generate_job_post'),
    path("generate-blog-post/", generate_blog_post, name="generate_blog_post"),
    path("submit-blog-post/", submit_blog_post, name="submit_blog_post"),
    path("blog-posts/", get_blog_posts, name="get_blog_posts"),
    path("jobs/", employer_jobs, name="employer_jobs"),
    path("generate-test/<int:job_id>/", generate_test, name="generate_test"),  #AI Test Generation
    path("save-test/<int:job_id>/", save_test, name="save_test"),
    path("update-blog-post/<int:post_id>/", update_blog_post, name="update_blog_post"),
    path("delete-blog-post/<int:post_id>/", delete_blog_post, name="delete_blog_post"),
    path("create-email/", create_email, name="create_email"),
    path("shortlist-candidates/", shortlist_candidates, name="shortlist_candidates"),
    path("create-order/", create_order, name="create_order"),
    path("recommend-candidates/", recommend_candidates, name="recommend_candidates"),
    path("generate-tests/", recommend_candidates, name="generate_tests"),
    path("logout/", employer_logout, name="employer_logout"),
    path('find-candidates/', find_candidates, name='find_candidates'),
    path("shortlist-candidate/", shortlist_candidate, name="shortlist_candidate"),
    path('job-candidates/<int:job_id>/', job_candidates_view, name='job_candidates'),
    path('get-shortlisted-candidates/', get_shortlisted_candidates, name='get_shortlisted_candidates'),
    path('search-candidates/', vsearch_candidates, name='search_candidates'),
    path('generate-email/', generate_email, name='generate_email'),
    path('send-emails/', send_emails, name='send_emails'),
    path("generate-contracts/", generate_contracts, name="generate_contracts"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)