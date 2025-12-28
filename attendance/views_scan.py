from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import IntegrityError
from .models import StudentProfile, Subject, AttendanceRecord
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
@login_required
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

        if not uuid_str or not subject_id:
            return JsonResponse(
                {"success": False, "message": "Missing required fields"}, status=400
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
