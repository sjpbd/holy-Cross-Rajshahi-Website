# admissions/payments.py
"""Pluggable payment gateway: JanataPay in production, a stub with simulate buttons for local dev."""
import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from . import janatapay
from .models import Application, PaymentAttempt
from .services import fee_as_decimal, mark_application_paid

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """A payment could not be started; the message is safe to show to the applicant."""


class PaymentGateway:
    name = 'base'
    hosted = False

    def start_payment(self, request, application):
        raise NotImplementedError

    def handle_ipn(self, request):
        raise NotImplementedError

    def verify(self, transaction_id):
        raise NotImplementedError


class StubPaymentGateway(PaymentGateway):
    name = 'stub'

    def start_payment(self, request, application):
        amount = fee_as_decimal(application)
        attempt = PaymentAttempt.objects.create(
            application=application,
            gateway=self.name,
            amount=amount,
            status=PaymentAttempt.Status.STARTED,
        )
        return reverse('admissions:payment', kwargs={'token': application.access_token})

    def handle_ipn(self, request):
        """Placeholder for the future gateway IPN. Idempotent by transaction_id."""
        transaction_id = (
            request.POST.get('tran_id')
            or request.POST.get('transaction_id')
            or request.GET.get('tran_id')
            or ''
        ).strip()
        status = (request.POST.get('status') or request.GET.get('status') or '').lower()
        token = request.POST.get('application_token') or request.GET.get('application_token')
        if not token:
            return None
        try:
            application = Application.objects.get(access_token=token)
        except Application.DoesNotExist:
            return None

        if transaction_id:
            existing = PaymentAttempt.objects.filter(
                transaction_id=transaction_id,
                status=PaymentAttempt.Status.SUCCESS,
            ).first()
            if existing:
                return existing.application

        payload = {k: request.POST.get(k) or request.GET.get(k) for k in request.POST.keys() | request.GET.keys()}
        if status in {'valid', 'success', 'paid'}:
            PaymentAttempt.objects.create(
                application=application,
                gateway=self.name,
                amount=fee_as_decimal(application),
                transaction_id=transaction_id,
                raw_payload=payload,
                status=PaymentAttempt.Status.SUCCESS,
            )
            return mark_application_paid(
                application,
                transaction_id=transaction_id,
                gateway=self.name,
                payload=payload,
            )
        PaymentAttempt.objects.create(
            application=application,
            gateway=self.name,
            amount=fee_as_decimal(application),
            transaction_id=transaction_id,
            raw_payload=payload,
            status=PaymentAttempt.Status.FAILED,
        )
        if not application.is_paid:
            application.status = Application.Status.PAYMENT_FAILED
            application.payment_status = Application.PaymentStatus.FAILED
            application.save(update_fields=['status', 'payment_status', 'updated_at'])
        return application

    def verify(self, transaction_id):
        return PaymentAttempt.objects.filter(
            transaction_id=transaction_id,
            status=PaymentAttempt.Status.SUCCESS,
        ).exists()

    def simulate_success(self, application, transaction_id=''):
        if not settings.DEBUG:
            raise PermissionError('Payment simulation is only available in DEBUG.')
        tid = transaction_id or f'stub-{application.pk}'
        PaymentAttempt.objects.create(
            application=application,
            gateway=self.name,
            amount=fee_as_decimal(application),
            transaction_id=tid,
            status=PaymentAttempt.Status.SUCCESS,
        )
        return mark_application_paid(application, transaction_id=tid, gateway=self.name)

    def simulate_failure(self, application):
        if not settings.DEBUG:
            raise PermissionError('Payment simulation is only available in DEBUG.')
        PaymentAttempt.objects.create(
            application=application,
            gateway=self.name,
            amount=fee_as_decimal(application),
            status=PaymentAttempt.Status.FAILED,
        )
        application.status = Application.Status.PAYMENT_FAILED
        application.payment_status = Application.PaymentStatus.FAILED
        application.save(update_fields=['status', 'payment_status', 'updated_at'])
        return application


def _append_admin_note(application, note):
    stamp = timezone.localtime().strftime('%Y-%m-%d %H:%M')
    line = f'[{stamp}] {note}'
    application.admin_notes = f'{application.admin_notes}\n{line}'.strip() if application.admin_notes else line
    application.save(update_fields=['admin_notes', 'updated_at'])


class JanataPayGateway(PaymentGateway):
    """Janata Bank hosted payment page. The redirect back is never trusted; every result is verified."""

    name = 'janatapay'
    hosted = True

    def __init__(self, client=None):
        self.client = client or janatapay.JanataPayClient()

    @staticmethod
    def new_reference_id(application):
        form = ''.join(ch for ch in (application.form_number or '') if ch.isalnum()).upper()
        return f'HC{form}{uuid.uuid4().hex[:8].upper()}'[:40]

    def start_payment(self, request, application):
        """Tokenize a new transaction and return the gateway URL to redirect the applicant to."""
        amount = fee_as_decimal(application)
        if amount <= 0:
            mark_application_paid(application, transaction_id=f'free-{application.pk}', gateway=self.name)
            return reverse('admissions:success', kwargs={'token': application.access_token})
        if amount != amount.to_integral_value():
            raise PaymentError('The application fee must be a whole number of Taka for online payment. '
                               'Please contact the school office.')

        attempt = PaymentAttempt.objects.create(
            application=application,
            gateway=self.name,
            amount=amount,
            reference_id=self.new_reference_id(application),
            status=PaymentAttempt.Status.STARTED,
        )
        description = f'Admission form {application.form_number}'.strip()
        try:
            result = self.client.tokenize(int(amount), attempt.reference_id, description)
        except janatapay.JanataPayError as exc:
            logger.warning('JanataPay tokenize failed for %s: %s', attempt.reference_id, exc)
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.gateway_status = str(exc)[:80]
            attempt.save(update_fields=['status', 'gateway_status', 'updated_at'])
            raise PaymentError('The payment gateway is not responding right now. Please try again in a few minutes.') from exc

        attempt.transaction_token = result['transaction_token']
        attempt.aes_key = result['aes_key']
        attempt.payment_url = result['payment_url']
        attempt.gateway_status_code = janatapay.STATUS_INITIATED
        attempt.gateway_status = 'Initiated'
        attempt.save(update_fields=[
            'transaction_token', 'aes_key', 'payment_url', 'gateway_status_code', 'gateway_status', 'updated_at',
        ])
        self._extend_slot_hold(application)
        return attempt.payment_url

    @staticmethod
    def _extend_slot_hold(application):
        if application.skips_viva_selection or not application.viva_slot_id:
            return
        until = timezone.now() + timedelta(minutes=settings.JANATAPAY_PAYMENT_WINDOW_MINUTES)
        if not application.slot_held_until or application.slot_held_until < until:
            application.slot_held_until = until
            application.save(update_fields=['slot_held_until', 'updated_at'])

    def verify_attempt(self, attempt):
        """Ask the gateway for the final status of an attempt and apply it. Idempotent."""
        application = attempt.application
        if attempt.status == PaymentAttempt.Status.REFUNDED:
            return attempt
        if attempt.status == PaymentAttempt.Status.SUCCESS and application.is_paid:
            return attempt
        if not attempt.reference_id or not attempt.transaction_token:
            return attempt

        result = self.client.verify(attempt.reference_id, attempt.transaction_token)
        code = result['status_code']
        attempt.gateway_status_code = code
        attempt.gateway_status = result['status'][:80]
        attempt.verified_amount = result['amount']
        attempt.ft_number = result['ft_number'][:80]
        attempt.verified_at = timezone.now()
        attempt.raw_payload = result['raw']
        if result['ft_number']:
            attempt.transaction_id = result['ft_number'][:120]

        if code == janatapay.STATUS_SUCCESS:
            if result['amount'] is not None and Decimal(result['amount']) == Decimal(attempt.amount):
                attempt.status = PaymentAttempt.Status.SUCCESS
                attempt.save()
                self._confirm(attempt)
            else:
                attempt.status = PaymentAttempt.Status.FAILED
                attempt.gateway_status = 'Amount mismatch'
                attempt.save()
                _append_admin_note(
                    application,
                    f'JanataPay {attempt.reference_id}: gateway reported success but amount '
                    f'{result["amount"]} does not match fee {attempt.amount}. Not marked paid.',
                )
        elif code == janatapay.STATUS_FAILED:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.save()
            self._mark_failed(application)
        elif code == janatapay.STATUS_CANCELED:
            attempt.status = PaymentAttempt.Status.CANCELLED
            attempt.save()
            self._mark_failed(application)
        elif code == janatapay.STATUS_REFUNDED:
            attempt.status = PaymentAttempt.Status.REFUNDED
            attempt.save()
            _append_admin_note(
                application,
                f'JanataPay {attempt.reference_id}: payment was REFUNDED by the gateway. Review this application.',
            )
        else:
            attempt.save()
        return attempt

    def _confirm(self, attempt):
        application = attempt.application
        lost_slot = not application.skips_viva_selection and not application.viva_slot_id
        mark_application_paid(
            application,
            transaction_id=attempt.transaction_id or attempt.reference_id,
            gateway=self.name,
            payload=attempt.raw_payload,
        )
        if lost_slot:
            _append_admin_note(
                application,
                f'Paid via JanataPay {attempt.reference_id} after the viva slot hold expired. '
                'Assign a viva slot manually.',
            )

    @staticmethod
    def _mark_failed(application):
        application.refresh_from_db()
        if application.is_paid:
            return
        if application.status in (Application.Status.AWAITING_PAYMENT, Application.Status.PAYMENT_FAILED):
            application.status = Application.Status.PAYMENT_FAILED
            application.payment_status = Application.PaymentStatus.FAILED
            application.save(update_fields=['status', 'payment_status', 'updated_at'])

    def handle_callback(self, reference_id):
        """Verify the attempt named by the gateway's refid. Returns the attempt or None."""
        attempt = (
            PaymentAttempt.objects.select_related('application')
            .filter(gateway=self.name, reference_id=reference_id)
            .first()
        )
        if attempt is None:
            return None
        return self.verify_attempt(attempt)

    def handle_ipn(self, request):
        reference_id = (request.GET.get('refid') or request.POST.get('refid') or '').strip()
        if not reference_id:
            return None
        attempt = self.handle_callback(reference_id)
        return attempt.application if attempt else None

    def verify(self, transaction_id):
        return PaymentAttempt.objects.filter(
            Q(reference_id=transaction_id) | Q(transaction_id=transaction_id),
            gateway=self.name,
            status=PaymentAttempt.Status.SUCCESS,
        ).exists()


def reconcile_pending_payments(min_age_minutes=5, max_age_hours=48, gateway=None):
    """Re-verify JanataPay attempts still waiting for a final status. Returns a dict of counts."""
    gateway = gateway or JanataPayGateway()
    now = timezone.now()
    attempts = (
        PaymentAttempt.objects.select_related('application')
        .filter(
            gateway=JanataPayGateway.name,
            status=PaymentAttempt.Status.STARTED,
            created_at__lte=now - timedelta(minutes=min_age_minutes),
            created_at__gte=now - timedelta(hours=max_age_hours),
        )
        .exclude(transaction_token='')
        .order_by('created_at')
    )
    counts = {'checked': 0, 'paid': 0, 'failed': 0, 'pending': 0, 'errors': 0}
    for attempt in attempts:
        counts['checked'] += 1
        try:
            gateway.verify_attempt(attempt)
        except janatapay.JanataPayError as exc:
            logger.warning('JanataPay reconcile failed for %s: %s', attempt.reference_id, exc)
            counts['errors'] += 1
            continue
        if attempt.status == PaymentAttempt.Status.SUCCESS:
            counts['paid'] += 1
        elif attempt.status == PaymentAttempt.Status.STARTED:
            counts['pending'] += 1
        else:
            counts['failed'] += 1

    stale = PaymentAttempt.objects.filter(
        gateway=JanataPayGateway.name,
        status=PaymentAttempt.Status.STARTED,
        created_at__lt=now - timedelta(hours=max_age_hours),
    )
    counts['expired'] = stale.update(status=PaymentAttempt.Status.EXPIRED, updated_at=now)
    return counts


GATEWAYS = {
    StubPaymentGateway.name: StubPaymentGateway,
    JanataPayGateway.name: JanataPayGateway,
}


def get_gateway(name=None):
    name = (name or settings.PAYMENT_GATEWAY or 'stub').lower()
    return GATEWAYS.get(name, StubPaymentGateway)()
