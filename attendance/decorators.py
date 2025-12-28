from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps


def role_required(*roles):
    """
    Decorator to restrict access to views based on user roles

    Usage:
        @role_required('PRINCIPAL')
        @role_required('TEACHER', 'PRINCIPAL')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                from django.urls import reverse

                return redirect(f"{reverse('login')}?next={request.path}")

            if request.user.role not in roles:
                raise PermissionDenied(
                    "You do not have permission to access this page."
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def student_required(view_func):
    """Decorator to restrict access to students only"""
    return role_required("STUDENT")(view_func)


def teacher_required(view_func):
    """Decorator to restrict access to teachers only"""
    return role_required("TEACHER")(view_func)


def principal_required(view_func):
    """Decorator to restrict access to principals only"""
    return role_required("PRINCIPAL")(view_func)


def admin_required(view_func):
    """Decorator to restrict access to super admins only"""
    return role_required("SUPERADMIN")(view_func)


def staff_required(view_func):
    """Decorator to restrict access to teachers, principals, and admins"""
    return role_required("TEACHER", "PRINCIPAL", "SUPERADMIN")(view_func)
