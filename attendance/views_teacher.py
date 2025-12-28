from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .decorators import teacher_required
from .models import (
    Subject,
    AttendanceRecord,
    StudentProfile,
    DailyAttendance,
    TeacherProfile,
    User,
)
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .forms import StudentRegistrationForm, SubjectForm


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


@teacher_required
def advisory_view(request):
    """View for teachers to monitor their advisory class daily attendance"""
    try:
        # Check if teacher profile exists
        if hasattr(request.user, "teacher_profile"):
            profile = request.user.teacher_profile
        else:
            # Auto-create if missing (optional, or handle as error)
            # For now, just handle as not assigned
            return render(request, "teacher/advisory.html", {"assigned": False})

        grade = profile.advisory_grade
        section = profile.advisory_section

        if not grade or not section:
            return render(request, "teacher/advisory.html", {"assigned": False})

        # Get students
        students = (
            StudentProfile.objects.filter(grade_level=grade, section=section)
            .select_related("user")
            .order_by("user__last_name")
        )

        today = datetime.now().date()
        daily_records = DailyAttendance.objects.filter(student__in=students, date=today)
        record_map = {r.student.id: r for r in daily_records}

        student_data = []
        present_count = 0
        late_count = 0

        for student in students:
            record = record_map.get(student.id)
            status = "PENDING"
            if record:
                status = record.status
                if status == "PRESENT":
                    present_count += 1
                if status == "LATE":
                    late_count += 1

            student_data.append(
                {"student": student, "record": record, "status": status}
            )

        context = {
            "assigned": True,
            "grade": grade,
            "section": section,
            "student_data": student_data,
            "today": today,
            "total_students": len(students),
            "present_count": present_count,
            "late_count": late_count,
            "absent_count": len(students)
            - present_count
            - late_count,  # Rough estimate
        }
        return render(request, "teacher/advisory.html", context)

    except Exception as e:
        # Log error?
        return render(
            request, "teacher/advisory.html", {"assigned": False, "error": str(e)}
        )


@teacher_required
def add_student_view(request):
    """View for teachers to add new students to their advisory class"""

    # Check assignment
    try:
        profile = request.user.teacher_profile
        if not profile.advisory_grade or not profile.advisory_section:
            from django.contrib import messages

            messages.error(request, "You do not have an advisory class assigned.")
            return redirect("teacher_dashboard")
    except TeacherProfile.DoesNotExist:
        from django.contrib import messages

        messages.error(request, "Teacher profile not found.")
        return redirect("teacher_dashboard")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Create User
            username = form.cleaned_data["student_id"]  # Use LRN as username
            password = "password123"  # Default password (should be changed)
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]

            # Check if user exists
            if User.objects.filter(username=username).exists():
                from django.contrib import messages

                messages.error(request, f"Student with LRN {username} already exists.")
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role="STUDENT",
                )

                # Create Profile
                student = form.save(commit=False)
                student.user = user
                student.grade_level = profile.advisory_grade
                student.section = profile.advisory_section
                student.save()

                from django.contrib import messages

                messages.success(
                    request, f"Student {first_name} {last_name} added to your advisory."
                )
                return redirect("advisory_view")
    else:
        form = StudentRegistrationForm()

    context = {
        "form": form,
        "grade": profile.advisory_grade,
        "section": profile.advisory_section,
    }
    return render(request, "teacher/add_student.html", context)


@teacher_required
def add_subject_view(request):
    """View for teachers to add their own subjects"""
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.teacher = request.user
            subject.save()
            from django.contrib import messages

            messages.success(request, f"Subject {subject.name} created successfully.")
            return redirect("teacher_dashboard")
    else:
        form = SubjectForm()

    return render(request, "teacher/add_subject.html", {"form": form})


@teacher_required
def edit_subject_view(request, subject_id):
    """View to edit an existing subject"""
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)

    if request.method == "POST":
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            from django.contrib import messages

            messages.success(request, f"Subject {subject.name} updated successfully.")
            return redirect("teacher_dashboard")
    else:
        form = SubjectForm(instance=subject)

    return render(
        request,
        "teacher/add_subject.html",
        {"form": form, "is_edit": True, "subject": subject},
    )


@teacher_required
def delete_subject_view(request, subject_id):
    """View to delete a subject"""
    if request.method == "POST":
        subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)
        subject_name = subject.name
        subject.delete()
        from django.contrib import messages

        messages.success(request, f"Subject {subject_name} deleted successfully.")
        return redirect("teacher_dashboard")

    return redirect("teacher_dashboard")
