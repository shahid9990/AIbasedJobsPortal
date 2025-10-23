"""
URL configuration for jobsclub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from .views import home, job_details, blog_details, candidate_profile_v


urlpatterns = [
    path('', home, name='home'), 
    path("admin/", admin.site.urls),
    path("employers/", include("employers.urls")),  # Include employer app URLs
    path("candidates/", include("candidates.urls")),
    path("job/<int:job_id>/", job_details, name="job_details"),  #Job details page
    path("blog/<int:blog_id>/", blog_details, name="blog_details"),  #Blog details page
    path("cprofile/<int:candidate_id>/", candidate_profile_v, name="candidate_profile_v"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

