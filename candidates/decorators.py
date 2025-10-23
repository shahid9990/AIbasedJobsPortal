from django.shortcuts import redirect

def candidate_required(view_func):
    """ Ensures only logged-in candidates can access views """
    def wrapper(request, *args, **kwargs):
        if "candidate_id" not in request.session:
            return redirect("/candidates/login/")  # Redirect to candidate login
        return view_func(request, *args, **kwargs)
    return wrapper
