# core/context_processors.py
from .models import SchoolInfo, AdmissionBanner


def school_info_context(request):
    """
    Context processor to inject school information into all templates.
    This makes the school logo, contact info, and social media links
    available globally across all pages.
    """
    banner = AdmissionBanner.objects.filter(is_active=True).first()
    return {
        'school_info': SchoolInfo.load(),
        'admission_banner': banner,
    }
