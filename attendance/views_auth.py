from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse


def login_view(request):
    """User login view with role-based redirection"""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(
                request, f"Welcome back, {user.get_full_name() or user.username}!"
            )

            # Role-based redirection
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)

            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "auth/login.html")


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


@login_required
def dashboard_view(request):
    """Main dashboard with role-based redirection"""
    user = request.user

    if user.role == "PRINCIPAL":
        return redirect("principal_dashboard")
    elif user.role == "TEACHER":
        return redirect("teacher_dashboard")
    elif user.role == "STUDENT":
        return redirect("student_dashboard")
    elif user.role == "SUPERADMIN":
        return redirect("/admin/")

    return render(request, "attendance/dashboard.html")
