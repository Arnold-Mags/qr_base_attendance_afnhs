from django.core.management.base import BaseCommand
from django.utils import timezone
from attendance.models import User, StudentProfile, Subject, AttendanceRecord
from datetime import datetime, timedelta, time
import random


class Command(BaseCommand):
    help = "Seed the database with sample data for testing"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...")

        # Create SuperAdmin
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser(
                username="admin",
                email="admin@scholarscan.edu",
                password="admin123",
                first_name="System",
                last_name="Administrator",
                role="SUPERADMIN",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Created SuperAdmin (username: admin, password: admin123)"
                )
            )

        # Create Principal
        if not User.objects.filter(username="principal").exists():
            principal = User.objects.create_user(
                username="principal",
                email="principal@scholarscan.edu",
                password="principal123",
                first_name="Maria",
                last_name="Santos",
                role="PRINCIPAL",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Created Principal (username: principal, password: principal123)"
                )
            )

        # Create Teachers
        teachers = []
        teacher_data = [
            ("teacher1", "Juan", "Dela Cruz"),
            ("teacher2", "Ana", "Reyes"),
            ("teacher3", "Pedro", "Garcia"),
        ]

        for username, first_name, last_name in teacher_data:
            if not User.objects.filter(username=username).exists():
                teacher = User.objects.create_user(
                    username=username,
                    email=f"{username}@scholarscan.edu",
                    password="teacher123",
                    first_name=first_name,
                    last_name=last_name,
                    role="TEACHER",
                )
                teachers.append(teacher)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created Teacher: {first_name} {last_name} (username: {username}, password: teacher123)"
                    )
                )
            else:
                teachers.append(User.objects.get(username=username))

        # Create Subjects
        subjects_data = [
            # Grade 7
            (
                "MATH7",
                "Mathematics 7",
                7,
                "A",
                teachers[0],
                ["MON", "WED", "FRI"],
                time(8, 0),
                time(9, 0),
            ),
            (
                "SCI7",
                "Science 7",
                7,
                "A",
                teachers[1],
                ["TUE", "THU"],
                time(9, 0),
                time(10, 30),
            ),
            (
                "ENG7",
                "English 7",
                7,
                "A",
                teachers[2],
                ["MON", "WED", "FRI"],
                time(10, 30),
                time(11, 30),
            ),
            # Grade 11 STEM
            (
                "GENCHEM",
                "General Chemistry",
                11,
                "STEM-A",
                teachers[0],
                ["MON", "WED", "FRI"],
                time(8, 0),
                time(9, 30),
            ),
            (
                "PRECAL",
                "Pre-Calculus",
                11,
                "STEM-A",
                teachers[1],
                ["TUE", "THU"],
                time(9, 30),
                time(11, 0),
            ),
        ]

        subjects = []
        for code, name, grade, section, teacher, days, start, end in subjects_data:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "grade_level": grade,
                    "section": section,
                    "teacher": teacher,
                    "days_of_week": days,
                    "start_time": start,
                    "end_time": end,
                },
            )
            subjects.append(subject)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created Subject: {code} - {name}")
                )

        # Create Students
        student_names = [
            ("student1", "Jose", "Rizal", 7, "A", None),
            ("student2", "Andres", "Bonifacio", 7, "A", None),
            ("student3", "Emilio", "Aguinaldo", 7, "A", None),
            ("student4", "Apolinario", "Mabini", 7, "A", None),
            ("student5", "Gabriela", "Silang", 7, "A", None),
            ("student6", "Melchora", "Aquino", 11, "STEM-A", "STEM"),
            ("student7", "Marcelo", "Del Pilar", 11, "STEM-A", "STEM"),
            ("student8", "Graciano", "Lopez Jaena", 11, "STEM-A", "STEM"),
        ]

        students = []
        for username, first_name, last_name, grade, section, strand in student_names:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@student.scholarscan.edu",
                    password="student123",
                    first_name=first_name,
                    last_name=last_name,
                    role="STUDENT",
                )

                student_profile = StudentProfile.objects.create(
                    user=user,
                    student_id=f"LRN{random.randint(100000000000, 999999999999)}",
                    grade_level=grade,
                    section=section,
                    strand=strand,
                    parent_name=f"Parent of {first_name}",
                    parent_contact=f"09{random.randint(100000000, 999999999)}",
                )

                # Enroll in appropriate subjects
                for subject in subjects:
                    if subject.grade_level == grade and subject.section == section:
                        subject.students.add(student_profile)

                students.append(student_profile)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created Student: {first_name} {last_name} (username: {username}, password: student123)"
                    )
                )
            else:
                user = User.objects.get(username=username)
                student_profile = user.student_profile
                students.append(student_profile)

        # Create sample attendance records for the past week
        today = timezone.now().date()
        for i in range(7):
            date = today - timedelta(days=i)

            for subject in subjects:
                # Get enrolled students
                enrolled_students = subject.students.all()

                for student in enrolled_students:
                    # Random attendance (80% present, 10% late, 10% absent)
                    rand = random.random()
                    if rand < 0.8:
                        status = "PRESENT"
                    elif rand < 0.9:
                        status = "LATE"
                    else:
                        status = "ABSENT"

                    # Create attendance record
                    AttendanceRecord.objects.get_or_create(
                        student=student,
                        subject=subject,
                        date=date,
                        defaults={
                            "status": status,
                            "scan_method": "QR" if status != "ABSENT" else "MANUAL",
                        },
                    )

        self.stdout.write(
            self.style.SUCCESS("✓ Created sample attendance records for the past week")
        )

        self.stdout.write(self.style.SUCCESS("\n=== Database seeding completed! ==="))
        self.stdout.write("\nLogin Credentials:")
        self.stdout.write("  SuperAdmin: admin / admin123")
        self.stdout.write("  Principal: principal / principal123")
        self.stdout.write("  Teachers: teacher1, teacher2, teacher3 / teacher123")
        self.stdout.write("  Students: student1-student8 / student123")
