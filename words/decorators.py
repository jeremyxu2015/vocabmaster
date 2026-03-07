from django.shortcuts import redirect
from functools import wraps

def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if not request.user.userprofile.is_teacher:
                return redirect('words:dashboard')
        except:
            return redirect('words:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view