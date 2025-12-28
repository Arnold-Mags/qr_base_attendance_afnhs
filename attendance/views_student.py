from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .decorators import student_required
from .models import AttendanceRecord
from .utils import calculate_attendance_percentage
from datetime import datetime, timedelta
from django.db.models import Count, Q
import calendar


@student_required
def student_dashboard(request):
    """Student dashboard with attendance calendar and statistics"""
    try:
        student_profile = request.user.student_profile
    except:
        from django.contrib import messages

        messages.error(request, "Student profile not found.")
        return render(request, "student/dashboard.html", {"has_profile": False})

    # Get current month's attendance
    today = datetime.now().date()
    first_day = today.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Get all attendance records for current month
    attendance_records = AttendanceRecord.objects.filter(
        student=student_profile, date__gte=first_day, date__lte=last_day
    ).select_related("subject")

    # Create calendar grid
    cal = calendar.Calendar(firstweekday=6)  # Start on Sunday
    month_days = cal.monthdayscalendar(today.year, today.month)

    calendar_grid = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": "", "status": None})
            else:
                date_obj = today.replace(day=day)
                date_str = date_obj.strftime("%Y-%m-%d")

                # Check attendance for this day
                day_records = attendance_records.filter(date=date_obj)
                day_status = "PENDING"
                if day_records.exists():
                    if day_records.filter(status="ABSENT").exists():
                        day_status = "absent"
                    elif day_records.filter(status="LATE").exists():
                        day_status = "late"
                    else:
                        day_status = "present"
                elif date_obj < today:
                    day_status = "no_class"

                week_data.append(
                    {
                        "day": day,
                        "date": date_str,
                        "status": day_status,
                        "is_today": date_obj == today,
                    }
                )
        calendar_grid.append(week_data)

    # Get attendance statistics per subject
    subjects = student_profile.subjects.all()
    subject_stats = []

    for subject in subjects:
        stats = calculate_attendance_percentage(
            student_profile, subject=subject, date_from=first_day, date_to=last_day
        )
        subject_stats.append({"subject": subject, "stats": stats})

    # Overall statistics
    overall_stats = calculate_attendance_percentage(
        student_profile, date_from=first_day, date_to=last_day
    )

    context = {
        "has_profile": True,
        "student": student_profile,
        "calendar_grid": calendar_grid,
        "subject_stats": subject_stats,
        "overall_stats": overall_stats,
        "current_month": today.strftime("%B %Y"),
        "today": today.strftime("%Y-%m-%d"),
    }

    return render(request, "student/dashboard.html", context)
