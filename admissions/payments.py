# admissions/payments.py
"""Pluggable payment gateway. Real SSLCommerz / bKash adapters can implement PaymentGateway later."""
from django.conf import settings
from django.urls import reverse

from .models import Application, PaymentAttempt
from .services import fee_as_decimal, mark_application_paid


class PaymentGateway:
    name = 'base'

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


def get_gateway():
    return StubPaymentGateway()
