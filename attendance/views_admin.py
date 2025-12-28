from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .decorators import staff_required
from .models import ParentNotification, SchoolSettings, StudentProfile
from django.contrib import messages
from .forms import SchoolSettingsForm


@staff_required
def notification_history(request):
    """View to see all parent notifications sent/failed"""
    notifications = ParentNotification.objects.all().select_related(
        "student__user", "attendance_record__subject"
    )

    # Simple filtering
    status_filter = request.GET.get("status")
    if status_filter:
        notifications = notifications.filter(status=status_filter)

    search_query = request.GET.get("search")
    if search_query:
        notifications = notifications.filter(
            student__user__last_name__icontains=search_query
        ) | notifications.filter(student__student_id__icontains=search_query)

    context = {
        "notifications": notifications,
    }
    return render(request, "admin/notification_history.html", context)


@staff_required
def school_settings_view(request):
    """View to configure school-wide attendance settings"""
    school_settings = SchoolSettings.get_settings()

    if request.method == "POST":
        form = SchoolSettingsForm(request.POST, request.FILES, instance=school_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated successfully.")
            return redirect("school_settings")
    else:
        form = SchoolSettingsForm(instance=school_settings)

    context = {
        "form": form,
        "settings": school_settings,
    }
    return render(request, "admin/settings.html", context)
