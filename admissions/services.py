# admissions/services.py
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_time

from .models import AdmissionSequence, Application, VivaSlot


class SlotUnavailable(Exception):
    pass


def _decrement_slot(slot_id):
    VivaSlot.objects.filter(pk=slot_id, booked_count__gt=0).update(
        booked_count=F('booked_count') - 1,
    )


def release_slot_hold(application, save=True):
    """Release a non-paid hold and clear the application's slot."""
    if not application.viva_slot_id:
        return
    if application.status == Application.Status.PAID:
        return
    _decrement_slot(application.viva_slot_id)
    application.viva_slot = None
    application.slot_held_until = None
    if save:
        application.save(update_fields=['viva_slot', 'slot_held_until', 'updated_at'])


def release_unpaid_holds_for_slot(slot):
    qs = Application.objects.filter(
        viva_slot=slot,
    ).exclude(status=Application.Status.PAID)
    for application in qs:
        application.viva_slot = None
        application.slot_held_until = None
        if application.status == Application.Status.AWAITING_PAYMENT:
            application.status = Application.Status.DRAFT
        application.save(update_fields=['viva_slot', 'slot_held_until', 'status', 'updated_at'])
        if slot.booked_count:
            _decrement_slot(slot.pk)
            slot.refresh_from_db(fields=['booked_count'])


def expire_slot_holds(now=None):
    now = now or timezone.now()
    stale = Application.objects.filter(
        slot_held_until__lt=now,
        viva_slot__isnull=False,
    ).exclude(status=Application.Status.PAID)
    count = 0
    for application in stale:
        release_slot_hold(application, save=False)
        if application.status == Application.Status.AWAITING_PAYMENT:
            application.status = Application.Status.DRAFT
            application.payment_status = Application.PaymentStatus.EXPIRED
        application.save(update_fields=[
            'viva_slot', 'slot_held_until', 'status', 'payment_status', 'updated_at',
        ])
        count += 1
    return count


def expire_old_drafts(now=None):
    now = now or timezone.now()
    count = 0
    drafts = Application.objects.filter(
        status__in=[Application.Status.DRAFT, Application.Status.AWAITING_PAYMENT, Application.Status.PAYMENT_FAILED],
    ).select_related('session')
    for application in drafts:
        days = application.session.draft_expiry_days or 14
        if application.created_at + timedelta(days=days) > now:
            continue
        if application.status != Application.Status.PAID:
            release_slot_hold(application, save=False)
            application.status = Application.Status.EXPIRED
            application.payment_status = Application.PaymentStatus.EXPIRED
            application.save(update_fields=[
                'viva_slot', 'slot_held_until', 'status', 'payment_status', 'updated_at',
            ])
            count += 1
    return count


def _slot_has_passed(slot, now=None):
    now = now or timezone.localtime()
    today = now.date()
    if slot.date < today:
        return True
    if slot.date == today and slot.start_time <= now.time():
        return True
    return False


def hold_slot(application, slot):
    expire_slot_holds()
    if slot.session_id != application.session_id:
        raise SlotUnavailable('This viva slot is not part of the current admission session.')
    if not slot.is_active:
        raise SlotUnavailable('This viva slot is not available.')
    if _slot_has_passed(slot):
        raise SlotUnavailable('This viva slot has already passed.')

    hold_until = timezone.now() + timedelta(minutes=application.session.slot_hold_minutes)

    with transaction.atomic():
        if (
            application.viva_slot_id == slot.pk
            and application.slot_held_until
            and application.slot_held_until > timezone.now()
        ):
            application.slot_held_until = hold_until
            application.save(update_fields=['slot_held_until', 'updated_at'])
            return application

        if application.viva_slot_id:
            _decrement_slot(application.viva_slot_id)

        updated = VivaSlot.objects.filter(
            pk=slot.pk,
            is_active=True,
            booked_count__lt=F('capacity'),
        ).update(booked_count=F('booked_count') + 1)
        if not updated:
            # Restore previous hold occupancy if we decremented it
            if application.viva_slot_id and application.viva_slot_id != slot.pk:
                VivaSlot.objects.filter(pk=application.viva_slot_id).update(
                    booked_count=F('booked_count') + 1,
                )
            raise SlotUnavailable('This viva slot is full. Please choose another time.')

        application.viva_slot_id = slot.pk
        application.slot_held_until = hold_until
        application.save(update_fields=['viva_slot', 'slot_held_until', 'updated_at'])
    return application


def assign_form_number(application):
    if application.form_number:
        return application.form_number
    year = application.session.year_prefix()
    yy = application.session.year_yy()
    class_code = application.admit_class.form_number_code() if application.admit_class_id else 'X'
    with transaction.atomic():
        sequence, _created = AdmissionSequence.objects.get_or_create(
            year=year,
            class_code=class_code,
            defaults={'last_number': 0},
        )
        AdmissionSequence.objects.filter(pk=sequence.pk).update(last_number=F('last_number') + 1)
        sequence.refresh_from_db()
        application.form_number = f'{class_code}-{yy}-{sequence.last_number:05d}'
        application.save(update_fields=['form_number', 'updated_at'])
    return application.form_number


def generate_slots(session, start_date, end_date, weekdays, times=None, capacity=None, skip_existing=True):
    times = times if times is not None else (session.default_slot_times or [])
    capacity = capacity if capacity is not None else session.default_slot_capacity
    created = 0
    skipped = 0
    current = start_date
    while current <= end_date:
        if current.weekday() in weekdays:
            for item in times:
                start = item['start'] if isinstance(item['start'], datetime) else parse_time(str(item['start']))
                end = item['end'] if isinstance(item['end'], datetime) else parse_time(str(item['end']))
                if start is None or end is None:
                    continue
                if skip_existing and VivaSlot.objects.filter(
                    session=session, date=current, start_time=start,
                ).exists():
                    skipped += 1
                    continue
                VivaSlot.objects.create(
                    session=session,
                    date=current,
                    start_time=start,
                    end_time=end,
                    capacity=capacity,
                )
                created += 1
        current += timedelta(days=1)
    return created, skipped


def mark_application_paid(application, payment_status=None, transaction_id='', gateway='stub', payload=None):
    """Idempotent: paid applications are left unchanged (no second PDF/email)."""
    from .emails import send_confirmation_email
    from .pdf import generate_and_store_pdf

    payment_status = payment_status or Application.PaymentStatus.PAID
    if application.is_paid:
        return application

    with transaction.atomic():
        assign_form_number(application)
        application.status = Application.Status.PAID
        application.payment_status = payment_status
        application.paid_at = timezone.now()
        application.slot_held_until = None
        if not application.submitted_at:
            application.submitted_at = application.paid_at
        application.save(update_fields=[
            'form_number', 'status', 'payment_status', 'paid_at',
            'submitted_at', 'slot_held_until', 'updated_at',
        ])

    generate_and_store_pdf(application)
    send_confirmation_email(application)
    return application


def cancel_application(application):
    if application.status == Application.Status.PAID:
        application.status = Application.Status.CANCELLED
        application.save(update_fields=['status', 'updated_at'])
        return
    release_slot_hold(application, save=False)
    application.status = Application.Status.CANCELLED
    application.save(update_fields=['status', 'viva_slot', 'slot_held_until', 'updated_at'])


def fee_as_decimal(application):
    amount = application.fee_amount()
    if amount is None:
        return Decimal('0.00')
    return Decimal(amount)
