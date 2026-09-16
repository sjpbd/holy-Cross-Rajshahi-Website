# admissions/views.py
import calendar as calmod
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import geo
from .constants import (
    RESUME_COOKIE,
    RESUME_COOKIE_MAX_AGE,
    STEP_DECLARATIONS,
    STEP_FAMILY,
    STEP_HINTS,
    STEP_LABELS,
    STEP_OTHERS,
    STEP_REVIEW,
    STEP_SLOT,
    STEP_STUDENT,
)
from .forms import (
    DeclarationsStepForm,
    FamilyStepForm,
    LookupForm,
    OthersStepForm,
    PreviousResultFormSet,
    ResumeForm,
    SiblingFormSet,
    SlotHoldForm,
    StudentStepForm,
)
from .models import AdmissionClass, AdmissionSession, Application, VivaSlot
from .payments import get_gateway
from .services import (
    SlotUnavailable,
    assign_form_number,
    expire_slot_holds,
    hold_slot,
    mark_application_paid,
)
from .utils import client_ip, lookup_rate_limited

LIVE_STATUSES = [
    Application.Status.DRAFT,
    Application.Status.AWAITING_PAYMENT,
    Application.Status.PAYMENT_FAILED,
]


def _set_resume_cookie(response, application):
    response.set_cookie(
        RESUME_COOKIE,
        str(application.resume_token),
        max_age=RESUME_COOKIE_MAX_AGE,
        httponly=True,
        samesite='Lax',
        secure=not settings.DEBUG,
    )
    return response


def _application_from_cookie(request, session=None):
    raw = request.COOKIES.get(RESUME_COOKIE)
    if not raw:
        return None
    qs = Application.objects.filter(resume_token=raw)
    if session:
        qs = qs.filter(session=session)
    return qs.first()


def _get_or_create_draft(request, session):
    application = _application_from_cookie(request, session)
    if application and application.status in LIVE_STATUSES:
        return application, False
    if application and application.is_paid:
        return application, False
    application = Application.objects.create(
        session=session,
        ip_address=client_ip(request),
        nationality='Bangladesh',
    )
    return application, True


def _require_open_session(request):
    session = AdmissionSession.get_open()
    if not session:
        messages.error(request, 'Admission is not open at this time.')
        return None
    return session


def _step_form(step, data=None, files=None, instance=None):
    if step == STEP_STUDENT:
        return StudentStepForm(data, files, instance=instance)
    if step == STEP_FAMILY:
        return FamilyStepForm(data, instance=instance)
    if step == STEP_OTHERS:
        return OthersStepForm(data, instance=instance)
    if step == STEP_DECLARATIONS:
        return DeclarationsStepForm(data, instance=instance)
    return None


def _can_visit_step(application, step):
    if application.is_paid:
        return False
    return 1 <= step <= max(application.wizard_step or 1, 1) and step <= STEP_REVIEW


def _address_state(application):
    return {
        'present': application.geo_payload('present'),
        'father': application.geo_payload('father'),
        'mother': application.geo_payload('mother'),
    }


@never_cache
@require_GET
def landing(request):
    session = AdmissionSession.objects.filter(is_open=True).first()
    open_now = bool(session and session.is_currently_open())
    return render(request, 'admissions/landing.html', {
        'session': session,
        'open_now': open_now,
        'open_classes': AdmissionClass.objects.filter(is_active=True),
        'page_title': 'Admission - Holy Cross School and College',
        'page_description': 'Apply for admission to Holy Cross School & College, Rajshahi.',
    })


@never_cache
@require_http_methods(['GET', 'POST'])
def apply(request):
    session = _require_open_session(request)
    if not session:
        return redirect('admissions:landing')

    application, created = _get_or_create_draft(request, session)
    if application.is_paid:
        response = redirect('admissions:success', token=application.access_token)
        return _set_resume_cookie(response, application)

    expire_slot_holds()
    application.refresh_from_db()

    try:
        step = int(request.GET.get('step') or application.wizard_step or STEP_STUDENT)
    except (TypeError, ValueError):
        step = STEP_STUDENT
    if step < STEP_STUDENT or step > STEP_REVIEW:
        step = STEP_STUDENT
    if not _can_visit_step(application, step):
        step = application.wizard_step or STEP_STUDENT

    form = None
    result_formset = None
    sibling_formset = None
    calendar_data = None

    if step == STEP_SLOT:
        selected = request.GET.get('date')
        selected_date = None
        if selected:
            try:
                selected_date = date.fromisoformat(selected)
            except ValueError:
                selected_date = None
        calendar_data = _calendar_context(
            session, request.GET.get('year'), request.GET.get('month'), selected_date,
        )
    elif step == STEP_REVIEW:
        pass
    elif step == STEP_FAMILY:
        if request.method == 'POST':
            form = FamilyStepForm(request.POST, instance=application)
            result_formset = PreviousResultFormSet(request.POST, instance=application, prefix='results')
        else:
            form = FamilyStepForm(instance=application)
            result_formset = PreviousResultFormSet(instance=application, prefix='results')
    elif step == STEP_OTHERS:
        if request.method == 'POST':
            form = OthersStepForm(request.POST, instance=application)
            sibling_formset = SiblingFormSet(request.POST, instance=application, prefix='siblings')
        else:
            form = OthersStepForm(instance=application)
            sibling_formset = SiblingFormSet(instance=application, prefix='siblings')
    else:
        form = _step_form(
            step,
            data=request.POST or None,
            files=request.FILES or None,
            instance=application,
        )

    if request.method == 'POST' and step == STEP_SLOT:
        hold_form = SlotHoldForm(request.POST, session=session)
        if hold_form.is_valid():
            try:
                hold_slot(application, hold_form.cleaned_data['slot_id'])
                application.wizard_step = max(application.wizard_step, STEP_REVIEW)
                application.save(update_fields=['wizard_step', 'updated_at'])
                response = redirect(f"{reverse('admissions:apply')}?step={STEP_REVIEW}")
                return _set_resume_cookie(response, application)
            except SlotUnavailable as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, 'Please choose a viva slot.')
        selected = request.POST.get('date') or request.GET.get('date')
        selected_date = None
        if selected:
            try:
                selected_date = date.fromisoformat(selected)
            except ValueError:
                selected_date = None
        calendar_data = _calendar_context(
            session, request.GET.get('year'), request.GET.get('month'), selected_date,
        )

    elif request.method == 'POST' and step == STEP_REVIEW:
        expire_slot_holds()
        application.refresh_from_db()
        if not application.hold_is_valid:
            messages.error(request, 'Your viva slot hold expired. Please choose a slot again.')
            response = redirect(f"{reverse('admissions:apply')}?step={STEP_SLOT}")
            return _set_resume_cookie(response, application)
        if not session.is_currently_open():
            messages.error(request, 'Admission is now closed.')
            return redirect('admissions:landing')
        assign_form_number(application)
        application.status = Application.Status.AWAITING_PAYMENT
        application.payment_status = Application.PaymentStatus.PENDING
        if not application.submitted_at:
            application.submitted_at = timezone.now()
        application.save(update_fields=['status', 'payment_status', 'submitted_at', 'updated_at'])
        gateway = get_gateway()
        pay_url = gateway.start_payment(request, application)
        response = redirect(pay_url)
        return _set_resume_cookie(response, application)

    elif request.method == 'POST' and form is not None:
        formsets_ok = True
        if step == STEP_FAMILY:
            if not result_formset.is_valid():
                formsets_ok = False
        if step == STEP_OTHERS:
            if not sibling_formset.is_valid():
                formsets_ok = False
            elif form.is_valid() and form.cleaned_data.get('has_other_child'):
                living = [
                    f for f in sibling_formset.forms
                    if not f.cleaned_data.get('DELETE')
                    and f.cleaned_data.get('name')
                    and f.cleaned_data.get('class_name')
                ]
                if not living:
                    form.add_error('has_other_child', 'Please add at least one sibling currently in this school.')
                    formsets_ok = False

        if form.is_valid() and formsets_ok:
            application = form.save()
            if step == STEP_FAMILY:
                result_formset.instance = application
                result_formset.save()
            if step == STEP_STUDENT and getattr(form, 'birth_reg_warning', ''):
                messages.warning(request, form.birth_reg_warning)
            if step == STEP_OTHERS:
                sibling_formset.instance = application
                sibling_formset.save()
            next_step = min(step + 1, STEP_REVIEW)
            application.wizard_step = max(application.wizard_step, next_step)
            application.save(update_fields=['wizard_step', 'updated_at'])
            response = redirect(f"{reverse('admissions:apply')}?step={next_step}")
            return _set_resume_cookie(response, application)

    if step == STEP_STUDENT and form and getattr(form, 'birth_reg_warning', '') and form.is_bound and form.is_valid():
        messages.warning(request, form.birth_reg_warning)

    context = {
        'session': session,
        'application': application,
        'step': step,
        'step_labels': STEP_LABELS,
        'step_hints': STEP_HINTS,
        'form': form,
        'result_formset': result_formset,
        'sibling_formset': sibling_formset,
        'calendar': calendar_data,
        'bd_geo': geo.tree(),
        'geo_divisions': geo.divisions(),
        'address_state': _address_state(application),
        'step_label': STEP_LABELS.get(step, 'Apply'),
        'step_hint': STEP_HINTS.get(step, ''),
        'page_title': 'Apply for Admission - Holy Cross School and College',
    }
    response = render(request, 'admissions/apply.html', context)
    return _set_resume_cookie(response, application)


def _calendar_context(session, year=None, month=None, selected_date=None):
    expire_slot_holds()
    today = timezone.localdate()
    try:
        year = int(year) if year else today.year
        month = int(month) if month else today.month
    except (TypeError, ValueError):
        year, month = today.year, today.month
    if month < 1 or month > 12:
        year, month = today.year, today.month

    first = date(year, month, 1)
    prev_month = first - timedelta(days=1)
    if month == 12:
        next_month_date = date(year + 1, 1, 1)
    else:
        next_month_date = date(year, month + 1, 1)

    slots = VivaSlot.objects.filter(
        session=session,
        is_active=True,
        date__year=year,
        date__month=month,
        date__gte=today,
    )
    remaining_by_day = {}
    for slot in slots:
        remaining_by_day[slot.date] = remaining_by_day.get(slot.date, 0) + slot.remaining

    weeks = []
    month_cal = calmod.Calendar(firstweekday=6)  # Sunday
    for week in month_cal.monthdatescalendar(year, month):
        days = []
        for day in week:
            in_month = day.month == month
            remaining = remaining_by_day.get(day, 0) if in_month else 0
            days.append({
                'date': day,
                'in_month': in_month,
                'is_today': day == today,
                'is_past': day < today,
                'has_slots': remaining > 0,
                'remaining': remaining,
                'selected': selected_date == day,
            })
        weeks.append(days)

    day_slots = []
    if selected_date:
        now = timezone.localtime()
        qs = VivaSlot.objects.filter(
            session=session,
            is_active=True,
            date=selected_date,
        ).order_by('start_time')
        for slot in qs:
            passed = selected_date < today or (
                selected_date == today and slot.start_time <= now.time()
            )
            day_slots.append({
                'slot': slot,
                'remaining': slot.remaining,
                'disabled': passed or slot.is_full,
            })

    return {
        'year': year,
        'month': month,
        'month_name': first.strftime('%B %Y'),
        'weeks': weeks,
        'prev_year': prev_month.year,
        'prev_month': prev_month.month,
        'next_year': next_month_date.year,
        'next_month': next_month_date.month,
        'selected_date': selected_date,
        'day_slots': day_slots,
    }


@never_cache
@require_GET
def calendar_partial(request):
    session = _require_open_session(request)
    if not session:
        return HttpResponse('Admission is closed.', status=403)
    selected = request.GET.get('date')
    selected_date = None
    if selected:
        try:
            selected_date = date.fromisoformat(selected)
        except ValueError:
            selected_date = None
    context = {
        'calendar': _calendar_context(
            session,
            request.GET.get('year'),
            request.GET.get('month'),
            selected_date,
        ),
        'application': _application_from_cookie(request, session),
    }
    return render(request, 'admissions/_calendar.html', context)


@never_cache
@require_http_methods(['GET', 'POST'])
def resume_application(request):
    session = AdmissionSession.get_open()
    form = ResumeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if lookup_rate_limited(request, 'resume'):
            messages.error(request, 'Too many attempts. Please wait a few minutes and try again.')
        else:
            application = Application.objects.filter(
                birth_registration_no=form.cleaned_data['birth_registration_no'].strip(),
                father_mobile=form.cleaned_data['father_mobile'],
                status__in=LIVE_STATUSES,
            ).order_by('-updated_at').first()
            if not application:
                messages.error(request, 'No in-progress application matched those details.')
            else:
                response = redirect('admissions:apply')
                return _set_resume_cookie(response, application)
    return render(request, 'admissions/resume.html', {
        'form': form,
        'session': session,
        'page_title': 'Continue application',
    })


@never_cache
@require_http_methods(['GET', 'POST'])
def lookup_application(request):
    form = LookupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if lookup_rate_limited(request, 'lookup'):
            messages.error(request, 'Too many attempts. Please wait a few minutes and try again.')
        else:
            application = Application.objects.filter(
                form_number__iexact=form.cleaned_data['form_number'],
                father_mobile=form.cleaned_data['father_mobile'],
            ).first()
            if not application or not application.is_paid:
                messages.error(request, 'No paid application matched those details.')
            else:
                return redirect('admissions:success', token=application.access_token)
    return render(request, 'admissions/lookup.html', {
        'form': form,
        'page_title': 'Reprint admission form',
    })


@never_cache
@require_GET
def payment_page(request, token):
    application = get_object_or_404(Application, access_token=token)
    if application.is_paid:
        return redirect('admissions:success', token=token)
    expire_slot_holds()
    application.refresh_from_db()
    if not application.hold_is_valid and application.status != Application.Status.PAID:
        messages.error(request, 'Your viva slot reservation expired. Please choose a slot again before paying.')
        response = redirect(f"{reverse('admissions:apply')}?step={STEP_SLOT}")
        return _set_resume_cookie(response, application)
    return render(request, 'admissions/payment.html', {
        'application': application,
        'debug': settings.DEBUG,
        'page_title': 'Admission payment',
    })


@never_cache
@require_POST
def simulate_payment(request, token):
    if not settings.DEBUG:
        raise Http404()
    application = get_object_or_404(Application, access_token=token)
    gateway = get_gateway()
    outcome = request.POST.get('outcome')
    try:
        if outcome == 'fail':
            gateway.simulate_failure(application)
            messages.error(request, 'Simulated payment failed. You may try again.')
            return redirect('admissions:payment', token=token)
        gateway.simulate_success(application)
    except PermissionError:
        raise Http404()
    return redirect('admissions:success', token=token)


@never_cache
@require_GET
def payment_success(request):
    """Future gateway redirect. Looks up the stub/IPN-updated application."""
    token = request.GET.get('application_token') or request.GET.get('token')
    if not token:
        messages.error(request, 'Payment could not be matched to an application.')
        return redirect('admissions:landing')
    application = get_object_or_404(Application, access_token=token)
    if application.is_paid:
        return redirect('admissions:success', token=application.access_token)
    gateway = get_gateway()
    gateway.handle_ipn(request)
    application.refresh_from_db()
    if application.is_paid:
        return redirect('admissions:success', token=application.access_token)
    messages.error(request, 'Payment is not confirmed yet. If you were charged, please contact the school office.')
    return redirect('admissions:payment', token=application.access_token)


@never_cache
@require_GET
def payment_fail(request):
    token = request.GET.get('application_token') or request.GET.get('token')
    if token:
        application = Application.objects.filter(access_token=token).first()
        if application and not application.is_paid:
            application.status = Application.Status.PAYMENT_FAILED
            application.payment_status = Application.PaymentStatus.FAILED
            application.save(update_fields=['status', 'payment_status', 'updated_at'])
            messages.error(request, 'Payment was not completed. You can try again.')
            return redirect('admissions:payment', token=application.access_token)
    messages.error(request, 'Payment was not completed.')
    return redirect('admissions:landing')


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def payment_ipn(request):
    application = get_gateway().handle_ipn(request)
    if application is None:
        return JsonResponse({'ok': False}, status=400)
    return JsonResponse({
        'ok': True,
        'form_number': application.form_number,
        'status': application.status,
        'payment_status': application.payment_status,
    })


@never_cache
@require_GET
def success(request, token):
    application = get_object_or_404(
        Application.objects.select_related('session', 'admit_class', 'viva_slot'),
        access_token=token,
    )
    if not application.is_paid:
        raise Http404()
    return render(request, 'admissions/success.html', {
        'application': application,
        'email_sent': bool(application.confirmation_email_sent_at),
        'email_error': application.confirmation_email_error,
        'page_title': f'Application {application.form_number}',
    })


@never_cache
@require_GET
def pdf_download(request, token):
    application = get_object_or_404(Application, access_token=token)
    if not application.is_paid or not application.form_pdf:
        raise Http404()
    return FileResponse(
        application.form_pdf.open('rb'),
        as_attachment=True,
        filename=f'{application.form_number}.pdf',
        content_type='application/pdf',
    )
