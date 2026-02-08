# core/context_processors.py
from .models import SchoolInfo


def school_info_context(request):
    """
    Context processor to inject school information into all templates.
    This makes the school logo, contact info, and social media links
    available globally across all pages.
    """
    return {
        'school_info': SchoolInfo.load()
    }
