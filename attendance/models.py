from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class User(AbstractUser):
    """Custom User model with role-based authentication"""

    ROLE_CHOICES = [
        ("SUPERADMIN", "Super Administrator"),
        ("PRINCIPAL", "Principal"),
        ("TEACHER", "Teacher"),
        ("STUDENT", "Student"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="STUDENT")

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class StudentProfile(models.Model):
    """Extended profile for students with academic information"""

    GRADE_LEVEL_CHOICES = [
        (7, "Grade 7"),
        (8, "Grade 8"),
        (9, "Grade 9"),
        (10, "Grade 10"),
        (11, "Grade 11"),
        (12, "Grade 12"),
    ]

    STRAND_CHOICES = [
        ("STEM", "Science, Technology, Engineering and Mathematics"),
        ("ABM", "Accountancy, Business and Management"),
        ("HUMSS", "Humanities and Social Sciences"),
        ("GAS", "General Academic Strand"),
        ("TVL", "Technical-Vocational-Livelihood"),
        ("ICT", "Information and Communications Technology"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(
        max_length=20, unique=True, help_text="Learner Reference Number (LRN)"
    )
    grade_level = models.IntegerField(choices=GRADE_LEVEL_CHOICES)
    section = models.CharField(max_length=50)
    strand = models.CharField(
        max_length=10,
        choices=STRAND_CHOICES,
        blank=True,
        null=True,
        help_text="Required for Grades 11-12",
    )
    photo = models.ImageField(upload_to="student_photos/", blank=True, null=True)
    uuid_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Parent/Guardian Information
    parent_name = models.CharField(max_length=200)
    parent_contact = models.CharField(
        max_length=15, help_text="Mobile number for SMS alerts"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_profiles"
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ["grade_level", "section", "user__last_name"]

    def __str__(self):
        return f"{self.user.get_full_name()} - Grade {self.grade_level} {self.section}"

    def save(self, *args, **kwargs):
        # Validate strand requirement for Grades 11-12
        if self.grade_level in [11, 12] and not self.strand:
            raise ValueError("Strand is required for Grades 11 and 12")
        super().save(*args, **kwargs)


class Subject(models.Model):
    """Subject/Course with schedule information"""

    DAYS_OF_WEEK = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
        ("SAT", "Saturday"),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    grade_level = models.IntegerField(
        choices=StudentProfile.GRADE_LEVEL_CHOICES,
        validators=[MinValueValidator(7), MaxValueValidator(12)],
    )
    section = models.CharField(max_length=50)
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subjects_taught",
        limit_choices_to={"role": "TEACHER"},
    )

    # Schedule
    days_of_week = models.JSONField(
        default=list,
        help_text='List of days when this subject is scheduled (e.g., ["MON", "WED", "FRI"])',
    )
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Enrollment
    students = models.ManyToManyField(
        StudentProfile, related_name="subjects", blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subjects"
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ["grade_level", "section", "name"]

    def __str__(self):
        return f"{self.code} - {self.name} (Grade {self.grade_level} {self.section})"


class AttendanceRecord(models.Model):
    """Individual attendance record for a student in a subject"""

    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("LATE", "Late"),
        ("ABSENT", "Absent"),
    ]

    SCAN_METHOD_CHOICES = [
        ("QR", "QR Code Scan"),
        ("MANUAL", "Manual Entry"),
    ]

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="attendance_records"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PRESENT")
    scan_method = models.CharField(
        max_length=10, choices=SCAN_METHOD_CHOICES, default="QR"
    )
    location_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Optional GPS/location data for future geofencing features",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attendance_records"
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ["-timestamp"]
        unique_together = ["student", "subject", "date"]

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.code} ({self.date}) - {self.status}"


class ParentNotification(models.Model):
    """Mock SMS notification system for parent alerts"""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
    ]

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="notifications"
    )
    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "parent_notifications"
        verbose_name = "Parent Notification"
        verbose_name_plural = "Parent Notifications"
        ordering = ["-sent_at"]


class SchoolSettings(models.Model):
    """Global configuration for the school attendance system"""

    school_name = models.CharField(max_length=200, default="ScholarScan Academy")
    absence_alert_threshold = models.IntegerField(
        default=3,
        help_text="Number of absences before triggering a warning notification",
    )
    enable_auto_sms = models.BooleanField(
        default=True, help_text="Automatically trigger notifications for every absence"
    )
    scan_tolerance_minutes = models.IntegerField(
        default=15, help_text="Minutes before/after class to allow scanning"
    )

    class Meta:
        verbose_name = "School Setting"
        verbose_name_plural = "School Settings"

    def __str__(self):
        return self.school_name

    @classmethod
    def get_settings(cls):
        """Helper to get the singleton settings object"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings
