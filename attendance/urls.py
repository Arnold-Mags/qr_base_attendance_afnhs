from django.urls import path
from . import (
    views_auth,
    views_scan,
    views_student,
    views_teacher,
    views_principal,
    views_admin,
)

urlpatterns = [
    # Authentication
    path("", views_auth.login_view, name="login"),
    path("logout/", views_auth.logout_view, name="logout"),
    path("dashboard/", views_auth.dashboard_view, name="dashboard"),
    # QR Scanning
    path("scan/", views_scan.scan_portal, name="scan_portal"),
    path("api/verify-scan/", views_scan.verify_scan, name="verify_scan"),
    # Student
    path(
        "student/dashboard/", views_student.student_dashboard, name="student_dashboard"
    ),
    path("student/digital-id/", views_scan.digital_id, name="digital_id"),
    # Teacher
    path(
        "teacher/dashboard/", views_teacher.teacher_dashboard, name="teacher_dashboard"
    ),
    path(
        "teacher/classroom/<int:subject_id>/",
        views_teacher.classroom_view,
        name="classroom_view",
    ),
    path(
        "teacher/mark-attendance/<int:subject_id>/",
        views_teacher.mark_manual_attendance,
        name="mark_manual_attendance",
    ),
    # Principal
    path(
        "principal/dashboard/",
        views_principal.principal_dashboard,
        name="principal_dashboard",
    ),
    # Administration
    path(
        "admin/notifications/",
        views_admin.notification_history,
        name="notification_history",
    ),
    path("admin/settings/", views_admin.school_settings_view, name="school_settings"),
]
