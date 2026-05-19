from django.shortcuts import redirect

class RestrictAdminMiddleware:
    """
    Prevents standard candidates from seeing the Django Admin login/error screen.
    If a non-staff user tries to access /admin/, they are redirected to the home page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Check if the user is trying to access the admin URL
        if request.path.startswith('/admin/'):
            
            # 2. Check if the user is logged in, but is NOT an HR admin (is_staff)
            if request.user.is_authenticated and not request.user.is_staff:
                
                # 3. Instantly kick them back to the job board!
                return redirect('job_list')
                
        # Otherwise, let the request through normally
        return self.get_response(request)