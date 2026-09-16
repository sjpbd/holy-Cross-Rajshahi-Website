# admissions/context_processors.py
from django.db.utils import OperationalError, ProgrammingError

from .models import AdmissionSession


def admission_context(request):
    try:
        session = AdmissionSession.get_open()
    except (OperationalError, ProgrammingError):
        session = None
    return {
        'admission_session_open': session,
    }
