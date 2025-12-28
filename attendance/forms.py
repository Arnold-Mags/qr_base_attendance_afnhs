from django import forms
from .models import StudentProfile, User, Subject, SchoolSettings


class StudentRegistrationForm(forms.ModelForm):
    """Form for teachers to register new students to their advisory"""

    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = StudentProfile
        fields = ["student_id", "strand", "photo", "parent_name", "parent_contact"]
        widgets = {
            "student_id": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "strand": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "parent_name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "parent_contact": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "photo": forms.FileInput(
                attrs={"class": "w-full px-4 py-2 border rounded-lg"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add simpler styling to first_name/last_name manual fields
        self.fields["first_name"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
            }
        )
        self.fields["last_name"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
            }
        )


class SubjectForm(forms.ModelForm):
    """Form for teachers to create their own subjects"""

    class Meta:
        model = Subject
        fields = [
            "name",
            "code",
            "grade_level",
            "section",
            "days_of_week",
            "start_time",
            "end_time",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500",
                    "placeholder": "e.g., Mathematics 10",
                }
            ),
            "code": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500",
                    "placeholder": "e.g., MATH10-A",
                }
            ),
            "grade_level": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500"
                }
            ),
            "section": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500",
                    "placeholder": "e.g., Einstein",
                }
            ),
            "days_of_week": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500",
                    "placeholder": 'e.g., ["MON", "WED"]',
                }
            ),
            "start_time": forms.TimeInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500",
                    "type": "time",
                }
            ),
            "end_time": forms.TimeInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500",
                    "type": "time",
                }
            ),
        }

    def clean_days_of_week(self):
        # Basic validation to ensure it's a list (JSONField)
        data = self.cleaned_data["days_of_week"]
        # If user types "MON, WED", convert to list. Ideally improve UI for this later.
        if isinstance(data, str):
            try:
                import json

                return json.loads(data)
            except:
                # Fallback: split by comma if not valid JSON
                return [d.strip().upper() for d in data.split(",")]
        return data


class SchoolSettingsForm(forms.ModelForm):
    """Form for configuring school-wide settings"""

    class Meta:
        model = SchoolSettings
        fields = [
            "school_name",
            "school_id",
            "school_logo",
            "address",
            "region",
            "division",
            "district",
            "province",
            "absence_alert_threshold",
            "enable_auto_sms",
            "scan_tolerance_minutes",
        ]
        widgets = {
            "school_name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "school_id": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "region": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "division": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "district": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "province": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "school_logo": forms.FileInput(
                attrs={"class": "w-full px-4 py-2 border rounded-lg"}
            ),
            "absence_alert_threshold": forms.NumberInput(
                attrs={
                    "class": "w-24 px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
            "scan_tolerance_minutes": forms.NumberInput(
                attrs={
                    "class": "w-24 px-4 py-2 border rounded-lg focus:ring-emerald-500 focus:border-emerald-500"
                }
            ),
        }
