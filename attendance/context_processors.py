from .models import SchoolSettings


def school_settings(request):
    """
    Context processor to make school settings available in all templates
    Usage: {{ school_settings.school_name }}
    """
    settings = SchoolSettings.get_settings()
    return {"school_settings": settings}
