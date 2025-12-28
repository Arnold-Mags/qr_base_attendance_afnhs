from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .decorators import principal_required
from .models import AttendanceRecord, StudentProfile, Subject
from django.db.models import Count, Q, Avg
from datetime import datetime, timedelta


@principal_required
def principal_dashboard(request):
    """Principal dashboard with school-wide analytics and heatmaps"""
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # School-wide statistics
    total_students = StudentProfile.objects.count()
    total_subjects = Subject.objects.count()

    # Today's attendance
    today_records = AttendanceRecord.objects.filter(date=today)
    today_present = today_records.filter(Q(status="PRESENT") | Q(status="LATE")).count()
    today_absent = today_records.filter(status="ABSENT").count()
    today_total = today_records.count()

    # Grade-level heatmap data (absence rates)
    grade_levels = [7, 8, 9, 10, 11, 12]
    heatmap_data = []

    for grade in grade_levels:
        students_in_grade = StudentProfile.objects.filter(grade_level=grade)
        total_in_grade = students_in_grade.count()

        if total_in_grade == 0:
            continue

        # Get this month's attendance for this grade
        month_records = AttendanceRecord.objects.filter(
            student__grade_level=grade, date__gte=month_start, date__lte=today
        )

        total_records = month_records.count()
        absent_records = month_records.filter(status="ABSENT").count()

        absence_rate = (
            (absent_records / total_records * 100) if total_records > 0 else 0
        )

        heatmap_data.append(
            {
                "grade_level": grade,
                "total_students": total_in_grade,
                "absence_rate": round(absence_rate, 1),
                "total_absences": absent_records,
            }
        )

    # Top 5 sections with highest absences
    sections_data = (
        AttendanceRecord.objects.filter(date__gte=month_start, status="ABSENT")
        .values("student__grade_level", "student__section")
        .annotate(absence_count=Count("id"))
        .order_by("-absence_count")[:5]
    )

    top_sections = []
    for section in sections_data:
        top_sections.append(
            {
                "grade_level": section["student__grade_level"],
                "section": section["student__section"],
                "absence_count": section["absence_count"],
            }
        )

    # Weekly trend data (for chart)
    weekly_trend = []
    for i in range(7):
        date = week_start + timedelta(days=i)
        if date > today:
            break

        day_records = AttendanceRecord.objects.filter(date=date)
        present = day_records.filter(Q(status="PRESENT") | Q(status="LATE")).count()
        absent = day_records.filter(status="ABSENT").count()

        weekly_trend.append(
            {
                "date": date.strftime("%a"),
                "present": present,
                "absent": absent,
                "total": present + absent,
            }
        )

    # Recent alerts (students marked absent today)
    recent_alerts = AttendanceRecord.objects.filter(
        date=today, status="ABSENT"
    ).select_related("student__user", "subject")[:10]

    context = {
        "total_students": total_students,
        "total_subjects": total_subjects,
        "today_present": today_present,
        "today_absent": today_absent,
        "today_total": today_total,
        "today_percentage": (
            round((today_present / today_total * 100), 1) if today_total > 0 else 0
        ),
        "heatmap_data": heatmap_data,
        "top_sections": top_sections,
        "weekly_trend": weekly_trend,
        "recent_alerts": recent_alerts,
        "current_month": today.strftime("%B %Y"),
    }

    return render(request, "principal/dashboard.html", context)
