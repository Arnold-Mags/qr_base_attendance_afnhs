import qrcode
from io import BytesIO
from django.core.files import File
from datetime import datetime, timedelta
from .models import ParentNotification


from django.core import signing
from django.conf import settings


def generate_qr_code(uuid_str):
    """
    Generate a secure QR code image with a timestamp signature

    Args:
        uuid_str: Student's UUID

    Returns:
        BytesIO object containing the QR code image
    """
    signer = signing.TimestampSigner()
    # Sign the UUID string
    signed_data = signer.sign(str(uuid_str))

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(signed_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer


def verify_qr_data(signed_data, max_age=300):
    """
    Verify the signed QR data and extract original UUID

    Args:
        signed_data: The data scanned from the QR
        max_age: Maximum age of the signature in seconds (default 5 mins)

    Returns:
        str: Original UUID if valid, None otherwise
    """
    signer = signing.TimestampSigner()
    try:
        uuid_str = signer.unsign(signed_data, max_age=max_age)
        return uuid_str
    except (signing.SignatureExpired, signing.BadSignature):
        return None


def is_within_time_window(subject, current_time, tolerance_minutes=None):
    """
    Check if the current time is within the subject's class schedule window
    """
    from .models import SchoolSettings

    settings = SchoolSettings.get_settings()

    if tolerance_minutes is None:
        tolerance_minutes = settings.scan_tolerance_minutes

    # Get current day of week (MON, TUE, etc.)
    day_mapping = {0: "MON", 1: "TUE", 2: "WED", 3: "THU", 4: "FRI", 5: "SAT", 6: "SUN"}
    current_day = day_mapping[current_time.weekday()]

    # Check if today is a scheduled day for this subject
    if current_day not in subject.days_of_week:
        return False, f"This subject is not scheduled on {current_day}"

    # Create datetime objects for comparison
    current_time_only = current_time.time()

    # Calculate tolerance window
    start_datetime = datetime.combine(current_time.date(), subject.start_time)
    end_datetime = datetime.combine(current_time.date(), subject.end_time)

    start_with_tolerance = (
        start_datetime - timedelta(minutes=tolerance_minutes)
    ).time()
    end_with_tolerance = (end_datetime + timedelta(minutes=tolerance_minutes)).time()

    # Check if current time is within the window
    if start_with_tolerance <= current_time_only <= end_with_tolerance:
        return True, "Scan successful"
    else:
        return (
            False,
            f"Scan outside class time. Class is from {subject.start_time.strftime('%I:%M %p')} to {subject.end_time.strftime('%I:%M %p')}",
        )


def trigger_parent_notification(attendance_record):
    """
    Create a mock SMS notification for parents based on SchoolSettings

    Args:
        attendance_record: AttendanceRecord instance

    Returns:
        ParentNotification instance or None
    """
    from .models import SchoolSettings, AttendanceRecord

    settings = SchoolSettings.get_settings()

    if attendance_record.status != "ABSENT":
        return None

    student = attendance_record.student
    subject = attendance_record.subject

    # Check if we should send immediate notification
    should_notify = settings.enable_auto_sms

    # If not auto-sms, check if threshold is reached
    if not should_notify:
        absence_count = AttendanceRecord.objects.filter(
            student=student, status="ABSENT"
        ).count()
        if absence_count >= settings.absence_alert_threshold:
            should_notify = True
            message_prefix = (
                f"ALERT (Threshold {settings.absence_alert_threshold} reached): "
            )
        else:
            return None
    else:
        message_prefix = ""

    message = (
        f"{message_prefix}Dear {student.parent_name},\n\n"
        f"Your child {student.user.get_full_name()} was marked ABSENT in "
        f"{subject.name} on {attendance_record.date.strftime('%B %d, %Y')}.\n\n"
        f"If you have any concerns, please contact the school.\n\n"
        f"- {settings.school_name} Attendance System"
    )

    notification = ParentNotification.objects.create(
        student=student,
        attendance_record=attendance_record,
        message=message,
        status="SENT",  # Mock as sent immediately
    )

    return notification


def calculate_attendance_percentage(
    student, subject=None, date_from=None, date_to=None
):
    """
    Calculate attendance percentage for a student

    Args:
        student: StudentProfile instance
        subject: Optional Subject instance to filter by specific subject
        date_from: Optional start date for filtering
        date_to: Optional end date for filtering

    Returns:
        dict: {'total': int, 'present': int, 'late': int, 'absent': int, 'percentage': float}
    """
    from .models import AttendanceRecord

    records = AttendanceRecord.objects.filter(student=student)

    if subject:
        records = records.filter(subject=subject)

    if date_from:
        records = records.filter(date__gte=date_from)

    if date_to:
        records = records.filter(date__lte=date_to)

    total = records.count()
    present = records.filter(status="PRESENT").count()
    late = records.filter(status="LATE").count()
    absent = records.filter(status="ABSENT").count()

    percentage = ((present + late) / total * 100) if total > 0 else 0

    return {
        "total": total,
        "present": present,
        "late": late,
        "absent": absent,
        "percentage": round(percentage, 2),
    }
