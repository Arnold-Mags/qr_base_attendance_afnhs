from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import IntegrityError
from .models import StudentProfile, Subject, AttendanceRecord, DailyAttendance
from .decorators import staff_required, student_required
from .utils import is_within_time_window, trigger_parent_notification, generate_qr_code
import json


@staff_required
def scan_portal(request):
    """QR code scanning portal for teachers and staff"""
    subjects = Subject.objects.all()

    if request.user.role == "TEACHER":
        subjects = subjects.filter(teacher=request.user)

    context = {
        "subjects": subjects,
    }
    return render(request, "scan/portal.html", context)


@require_http_methods(["POST"])
def verify_scan(request):
    """
    API endpoint to verify QR code scan and create attendance record

    Expected POST data:
    - uuid: Student's UUID from QR code
    - subject_id: Subject ID
    """
    try:
        data = json.loads(request.body)
        uuid_str = data.get("uuid")
        subject_id = data.get("subject_id")
        location_data = data.get("location_data")

        if not uuid_str:
            return JsonResponse(
                {"success": False, "message": "Missing QR code data"}, status=400
            )

        # Verify QR code signature and timestamp
        from .utils import verify_qr_data

        actual_uuid = verify_qr_data(uuid_str)

        if not actual_uuid:
            return JsonResponse(
                {
                    "success": False,
                    "message": "QR code expired or invalid. Please refresh Digital ID.",
                },
                status=403,
            )

        # Verify student exists
        try:
            student = StudentProfile.objects.get(uuid_code=actual_uuid)
        except StudentProfile.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Student not found."},
                status=404,
            )

        # --- GENERAL ATTENDANCE LOGIC (If no subject_id) ---
        if not subject_id:
            return process_general_attendance(student)

        # Verify subject exists
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Subject not found."}, status=404
            )

        # Check if student is enrolled in subject
        if not subject.students.filter(id=student.id).exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": f"{student.user.get_full_name()} is not enrolled in {subject.name}.",
                },
                status=403,
            )

        # Verify time window
        current_time = timezone.now()
        is_valid, message = is_within_time_window(subject, current_time)

        if not is_valid:
            return JsonResponse({"success": False, "message": message}, status=403)

        # Determine status based on time
        status = "PRESENT"
        time_diff = (current_time.time().hour * 60 + current_time.time().minute) - (
            subject.start_time.hour * 60 + subject.start_time.minute
        )

        if time_diff > 10:  # More than 10 minutes late
            status = "LATE"

        # Create attendance record
        try:
            attendance = AttendanceRecord.objects.create(
                student=student,
                subject=subject,
                status=status,
                scan_method="QR",
                location_data=location_data,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Attendance recorded for {student.user.get_full_name()}",
                    "data": {
                        "student_name": student.user.get_full_name(),
                        "student_id": student.student_id,
                        "grade_level": student.grade_level,
                        "section": student.section,
                        "subject": subject.name,
                        "status": status,
                        "timestamp": attendance.timestamp.strftime("%I:%M %p"),
                    },
                }
            )

        except IntegrityError:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"{student.user.get_full_name()} has already been marked for {subject.name} today.",
                },
                status=409,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"}, status=400
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"An error occurred: {str(e)}"}, status=500
        )


@student_required
def digital_id(request):
    """Student's digital ID page with QR code"""
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        from django.contrib import messages

        messages.error(
            request, "Student profile not found. Please contact administrator."
        )
        return render(request, "student/digital_id.html", {"has_profile": False})

    # Generate QR code
    qr_buffer = generate_qr_code(student_profile.uuid_code)

    # Convert to base64 for display
    import base64

    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()

    context = {
        "has_profile": True,
        "student": student_profile,
        "qr_code": qr_base64,
    }

    return render(request, "student/digital_id.html", context)


def gate_scanner(request):
    """Standalone Gate Scanner View (Public/Kiosk Mode)"""
    subjects = Subject.objects.all()

    # If logged-in teacher, only show their subjects (optional)
    if request.user.is_authenticated and request.user.role == "TEACHER":
        subjects = subjects.filter(teacher=request.user)

    context = {
        "subjects": subjects,
        "hide_nav": True,
    }
    return render(request, "scan/gate_scanner.html", context)


def process_general_attendance(student):
    """
    Handle General Attendance Logic (Gate Log)

    Schedule:
    - TIME IN MORNING: 7:00 AM - 8:00 AM (Late after 8:00 AM)
    - TIME OUT MORNING: 12:00 PM
    - TIME IN AFTERNOON: 1:00 PM
    - TIME OUT AFTERNOON: 4:00 PM - 5:00 PM
    """
    now = timezone.localtime()
    today = now.date()
    current_time = now.time()

    attendance, created = DailyAttendance.objects.get_or_create(
        student=student, date=today
    )

    action = None
    message = ""

    # Define Time Windows
    seven_am = timezone.datetime.strptime("07:00", "%H:%M").time()
    eight_am = timezone.datetime.strptime("08:00", "%H:%M").time()
    twelve_pm = timezone.datetime.strptime("12:00", "%H:%M").time()
    one_pm = timezone.datetime.strptime("13:00", "%H:%M").time()
    four_pm = timezone.datetime.strptime("16:00", "%H:%M").time()
    five_pm = timezone.datetime.strptime("17:00", "%H:%M").time()

    # 1. MORNING ENTRY
    if current_time < twelve_pm:
        if not attendance.time_in_am:
            attendance.time_in_am = current_time
            if current_time > eight_am:
                attendance.status = "LATE"
                attendance.minutes_late = (
                    current_time.hour * 60 + current_time.minute
                ) - (8 * 60)
                message = "Morning Time In (LATE)"
            else:
                attendance.status = "PRESENT"
                message = "Morning Time In (Success)"
            action = "TIME_IN_AM"
            attendance.save()
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Already timed in for morning at {attendance.time_in_am.strftime('%I:%M %p')}.",
                },
                status=409,
            )

    # 2. MORNING EXIT (Around 12:00 PM)
    elif twelve_pm <= current_time < one_pm:
        if not attendance.time_out_am:
            attendance.time_out_am = current_time
            message = "Morning Time Out (Success)"
            action = "TIME_OUT_AM"
            attendance.save()
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Already timed out for morning at {attendance.time_out_am.strftime('%I:%M %p')}.",
                },
                status=409,
            )

    # 3. AFTERNOON ENTRY (Around 1:00 PM)
    elif one_pm <= current_time < four_pm:
        # Note: If student skipped morning, we might need to handle creation.
        # But get_or_create handles creation.
        if not attendance.time_in_pm:
            attendance.time_in_pm = current_time
            message = "Afternoon Time In (Success)"
            action = "TIME_IN_PM"
            # If they were absent in morning, status remains as is or update logic?
            # For now, keep simple.
            attendance.save()
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Already timed in for afternoon at {attendance.time_in_pm.strftime('%I:%M %p')}.",
                },
                status=409,
            )

    # 4. AFTERNOON EXIT (4:00 PM - 5:00 PM+)
    elif current_time >= four_pm:
        if not attendance.time_out_pm:
            attendance.time_out_pm = current_time
            message = "Afternoon Time Out (Success)"
            action = "TIME_OUT_PM"
            attendance.save()
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Already timed out for afternoon at {attendance.time_out_pm.strftime('%I:%M %p')}.",
                },
                status=409,
            )

    # SEND NOTIFICATION (Mock)
    if action:
        trigger_parent_notification(
            student,
            None,
            f"{student.user.first_name}: {message} at {now.strftime('%I:%M %p')}",
        )

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "data": {
                "student_name": student.user.get_full_name(),
                "grade_level": student.grade_level,
                "section": student.section,
                "status": attendance.status,
                "timestamp": now.strftime("%I:%M %p"),
                "action": action,
            },
        }
    )
