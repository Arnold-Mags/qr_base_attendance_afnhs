from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .decorators import teacher_required
from .models import Subject, AttendanceRecord, StudentProfile
from django.db.models import Count, Q
from datetime import datetime, timedelta


@teacher_required
def teacher_dashboard(request):
    """Teacher dashboard with assigned subjects and quick stats"""
    subjects = Subject.objects.filter(teacher=request.user).prefetch_related("students")

    subject_stats = []
    for subject in subjects:
        today = datetime.now().date()

        # Get today's attendance
        today_attendance = AttendanceRecord.objects.filter(
            subject=subject, date=today
        ).count()

        total_students = subject.students.count()

        # Get this week's stats
        week_start = today - timedelta(days=today.weekday())
        week_attendance = (
            AttendanceRecord.objects.filter(
                subject=subject, date__gte=week_start, date__lte=today
            )
            .values("status")
            .annotate(count=Count("id"))
        )

        week_stats = {"PRESENT": 0, "LATE": 0, "ABSENT": 0}
        for stat in week_attendance:
            week_stats[stat["status"]] = stat["count"]

        subject_stats.append(
            {
                "subject": subject,
                "total_students": total_students,
                "today_attendance": today_attendance,
                "week_stats": week_stats,
            }
        )

    context = {
        "subject_stats": subject_stats,
    }

    return render(request, "teacher/dashboard.html", context)


@teacher_required
def classroom_view(request, subject_id):
    """Classroom view with student photo grid and real-time attendance"""
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)

    # Get all enrolled students
    students = subject.students.all().select_related("user")

    # Get today's attendance records
    today = datetime.now().date()
    attendance_records = AttendanceRecord.objects.filter(
        subject=subject, date=today
    ).select_related("student")

    # Create attendance map
    attendance_map = {record.student.id: record for record in attendance_records}

    # Prepare student data with attendance status
    student_data = []
    for student in students:
        attendance = attendance_map.get(student.id)
        student_data.append(
            {
                "student": student,
                "attendance": attendance,
                "status": attendance.status if attendance else "PENDING",
            }
        )

    # Statistics
    total_students = len(student_data)
    present_count = sum(1 for s in student_data if s["status"] == "PRESENT")
    late_count = sum(1 for s in student_data if s["status"] == "LATE")
    absent_count = sum(1 for s in student_data if s["status"] == "ABSENT")
    pending_count = sum(1 for s in student_data if s["status"] == "PENDING")

    context = {
        "subject": subject,
        "student_data": student_data,
        "total_students": total_students,
        "present_count": present_count,
        "late_count": late_count,
        "absent_count": absent_count,
        "pending_count": pending_count,
        "attendance_percentage": (
            round((present_count + late_count) / total_students * 100, 1)
            if total_students > 0
            else 0
        ),
    }

    return render(request, "teacher/classroom.html", context)


@teacher_required
def mark_manual_attendance(request, subject_id):
    """Manual attendance marking for teachers"""
    if request.method == "POST":
        subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)
        student_id = request.POST.get("student_id")
        status = request.POST.get("status")

        student = get_object_or_404(StudentProfile, id=student_id)

        # Check if student is enrolled
        if not subject.students.filter(id=student.id).exists():
            from django.contrib import messages

            messages.error(request, "Student not enrolled in this subject.")
            return redirect("classroom_view", subject_id=subject_id)

        # Create or update attendance record
        attendance, created = AttendanceRecord.objects.update_or_create(
            student=student,
            subject=subject,
            date=datetime.now().date(),
            defaults={"status": status, "scan_method": "MANUAL"},
        )

        from django.contrib import messages
        from .utils import trigger_parent_notification

        if status == "ABSENT":
            trigger_parent_notification(attendance)

        messages.success(
            request, f"Attendance marked for {student.user.get_full_name()}"
        )

        from django.shortcuts import redirect

        return redirect("classroom_view", subject_id=subject_id)

    return redirect("teacher_dashboard")
