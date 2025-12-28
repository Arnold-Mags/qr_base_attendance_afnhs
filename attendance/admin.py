from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StudentProfile, Subject, AttendanceRecord, ParentNotification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""

    list_display = ["username", "email", "first_name", "last_name", "role", "is_active"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name"]

    fieldsets = BaseUserAdmin.fieldsets + (("Role Information", {"fields": ("role",)}),)

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Role Information", {"fields": ("role",)}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Student Profile admin"""

    list_display = [
        "student_id",
        "get_full_name",
        "grade_level",
        "section",
        "strand",
        "parent_contact",
    ]
    list_filter = ["grade_level", "section", "strand"]
    search_fields = ["student_id", "user__first_name", "user__last_name", "parent_name"]
    readonly_fields = ["uuid_code", "created_at", "updated_at"]

    fieldsets = (
        ("User Information", {"fields": ("user",)}),
        (
            "Academic Information",
            {"fields": ("student_id", "grade_level", "section", "strand", "photo")},
        ),
        ("Parent/Guardian Information", {"fields": ("parent_name", "parent_contact")}),
        (
            "System Information",
            {
                "fields": ("uuid_code", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    get_full_name.short_description = "Full Name"


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Subject admin"""

    list_display = [
        "code",
        "name",
        "grade_level",
        "section",
        "teacher",
        "start_time",
        "end_time",
    ]
    list_filter = ["grade_level", "section", "teacher"]
    search_fields = ["code", "name"]
    filter_horizontal = ["students"]

    fieldsets = (
        (
            "Subject Information",
            {"fields": ("name", "code", "grade_level", "section", "teacher")},
        ),
        ("Schedule", {"fields": ("days_of_week", "start_time", "end_time")}),
        ("Enrollment", {"fields": ("students",)}),
    )


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """Attendance Record admin"""

    list_display = ["student", "subject", "date", "timestamp", "status", "scan_method"]
    list_filter = ["status", "scan_method", "date", "subject"]
    search_fields = [
        "student__user__first_name",
        "student__user__last_name",
        "student__student_id",
    ]
    readonly_fields = ["date", "timestamp", "created_at"]
    date_hierarchy = "date"

    fieldsets = (
        (
            "Attendance Information",
            {"fields": ("student", "subject", "status", "scan_method")},
        ),
        ("Timestamp", {"fields": ("date", "timestamp", "created_at")}),
        ("Additional Data", {"fields": ("location_data",), "classes": ("collapse",)}),
    )


@admin.register(ParentNotification)
class ParentNotificationAdmin(admin.ModelAdmin):
    """Parent Notification admin"""

    list_display = ["student", "get_parent_name", "status", "sent_at"]
    list_filter = ["status", "sent_at"]
    search_fields = [
        "student__user__first_name",
        "student__user__last_name",
        "student__parent_name",
    ]
    readonly_fields = ["sent_at"]

    fieldsets = (
        (
            "Notification Information",
            {"fields": ("student", "attendance_record", "message", "status")},
        ),
        ("Timestamp", {"fields": ("sent_at",)}),
    )

    def get_parent_name(self, obj):
        return obj.student.parent_name

    get_parent_name.short_description = "Parent Name"
