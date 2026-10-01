# admissions/pdf.py
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from core.models import SchoolInfo

from .constants import DECLARATION_AGREE, DECLARATION_INTRO, DECLARATIONS


def _file_uri(path):
    if not path:
        return ''
    return Path(path).resolve().as_uri()


def _static_font_uri(filename):
    path = Path(settings.BASE_DIR) / 'static' / 'fonts' / filename
    if path.exists():
        return _file_uri(path)
    return ''


def _yn(value):
    if value is True:
        return 'Yes'
    if value is False:
        return 'No'
    return ''


def build_pdf_context(application):
    school = SchoolInfo.load()
    logo_path = ''
    if school.logo:
        logo_path = _file_uri(school.logo.path)
    else:
        fallback = Path(settings.BASE_DIR) / 'static' / 'images' / 'og-logo.png'
        if fallback.exists():
            logo_path = _file_uri(fallback)

    photo_path = ''
    if application.photo:
        try:
            photo_path = _file_uri(application.photo.path)
        except ValueError:
            photo_path = ''

    signature_path = ''
    if application.session.principal_signature:
        try:
            signature_path = _file_uri(application.session.principal_signature.path)
        except ValueError:
            signature_path = ''

    siblings = [
        {'name': row.name, 'class_name': row.class_name}
        for row in application.siblings.all()
    ]
    while len(siblings) < 2:
        siblings.append({'name': '', 'class_name': ''})

    results = [
        row for row in application.previous_results.all()
        if row.previous_class or row.exam or row.year or row.result
    ]

    return {
        'application': application,
        'school': school,
        'logo_uri': logo_path,
        'photo_uri': photo_path,
        'signature_uri': signature_path,
        'font_regular': _static_font_uri('NotoSans-Regular.ttf'),
        'font_bold': _static_font_uri('NotoSans-Bold.ttf'),
        'font_bengali': _static_font_uri('NotoSansBengali-Regular.ttf'),
        'form_year': application.session.year_prefix(),
        'results': results,
        'siblings': siblings,
        'admit_instructions': application.admit_instructions(),
        'declaration_intro': DECLARATION_INTRO,
        'declarations': DECLARATIONS,
        'declaration_agree': DECLARATION_AGREE,
        'declaration_agreed': bool(
            application.agrees_uniform and application.agrees_rules and application.info_correct
        ),
        'answers': {
            'needs_bus': 'Yes' if application.needs_bus else 'No',
            'has_other_child': 'Yes' if application.has_other_child else 'No',
            'studied_here_before': _yn(application.studied_here_before),
        },
    }


def render_pdf_bytes(application):
    from weasyprint import HTML

    html = render_to_string('admissions/pdf/application.html', build_pdf_context(application))
    base_url = Path(settings.BASE_DIR).as_uri() + '/'
    return HTML(string=html, base_url=base_url).write_pdf()


def generate_and_store_pdf(application, force=False):
    if application.form_pdf and not force:
        return application
    pdf_bytes = render_pdf_bytes(application)
    filename = f'{application.form_number or application.resume_token}.pdf'
    if application.form_pdf:
        application.form_pdf.delete(save=False)
    application.form_pdf.save(filename, ContentFile(pdf_bytes), save=True)
    return application
