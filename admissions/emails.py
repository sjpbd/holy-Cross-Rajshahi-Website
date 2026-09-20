# admissions/emails.py
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_confirmation_email(application, force=False, request=None):
    """Best-effort: never raises to the caller after payment is recorded."""
    if application.confirmation_email_sent_at and not force:
        return True
    if not application.email:
        application.confirmation_email_error = 'No email address on the application.'
        application.save(update_fields=['confirmation_email_error', 'updated_at'])
        return False

    download_url = ''
    if request:
        download_url = request.build_absolute_uri(
            reverse('admissions:pdf_download', kwargs={'token': application.access_token})
        )
    else:
        try:
            download_url = reverse('admissions:pdf_download', kwargs={'token': application.access_token})
        except Exception:
            download_url = ''

    context = {
        'application': application,
        'download_url': download_url,
    }
    subject = (
        f'Admission Application {application.form_number} — '
        'Holy Cross School & College, Rajshahi'
    )
    text_body = render_to_string('admissions/email/confirmation.txt', context)
    html_body = render_to_string('admissions/email/confirmation.html', context)

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.email],
        )
        message.attach_alternative(html_body, 'text/html')
        if application.form_pdf:
            application.form_pdf.open('rb')
            try:
                filename = f'{application.form_number or "admission-form"}.pdf'
                message.attach(filename, application.form_pdf.read(), 'application/pdf')
            finally:
                application.form_pdf.close()
        message.send(fail_silently=False)
    except Exception as exc:
        logger.exception('Admission confirmation email failed for %s', application.pk)
        application.confirmation_email_error = str(exc)
        application.save(update_fields=['confirmation_email_error', 'updated_at'])
        return False

    application.confirmation_email_sent_at = timezone.now()
    application.confirmation_email_error = ''
    application.save(update_fields=['confirmation_email_sent_at', 'confirmation_email_error', 'updated_at'])
    return True
