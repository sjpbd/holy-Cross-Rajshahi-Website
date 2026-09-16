# admissions/admin.py
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .emails import send_confirmation_email
from .excel import applications_workbook
from .forms import GenerateSlotsForm
from .models import (
    AdmissionClass,
    AdmissionSequence,
    AdmissionSession,
    Application,
    BusStop,
    PaymentAttempt,
    PreviousResult,
    Sibling,
    VivaSlot,
)
from .pdf import generate_and_store_pdf
from .services import cancel_application, generate_slots, mark_application_paid


class PreviousResultInline(admin.TabularInline):
    model = PreviousResult
    extra = 0


class SiblingInline(admin.TabularInline):
    model = Sibling
    extra = 0
    fields = ['name', 'class_name']


class PaymentAttemptInline(admin.TabularInline):
    model = PaymentAttempt
    extra = 0
    readonly_fields = ['gateway', 'amount', 'transaction_id', 'status', 'raw_payload', 'created_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AdmissionSession)
class AdmissionSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'academic_year', 'is_open', 'opens_at', 'closes_at', 'default_slot_capacity', 'generate_slots_link']
    list_filter = ['is_open']
    fieldsets = (
        (None, {'fields': ('name', 'academic_year', 'is_open', 'opens_at', 'closes_at', 'instructions')}),
        ('Age & fee', {'fields': ('age_as_of_date', 'application_fee', 'draft_expiry_days')}),
        ('Viva slots', {
            'fields': (
                'default_slot_capacity',
                'slot_hold_minutes',
                'default_slot_times',
                'viva_venue',
                'principal_signature',
            ),
        }),
    )

    def generate_slots_link(self, obj):
        url = reverse('admin:admissions_generateslots', args=[obj.pk])
        return format_html('<a class="button" href="{}">Auto-create slots</a>', url)
    generate_slots_link.short_description = 'Slots'

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                '<int:session_id>/generate-slots/',
                self.admin_site.admin_view(self.generate_slots_view),
                name='admissions_generateslots',
            ),
        ]
        return extra + urls

    def generate_slots_view(self, request, session_id):
        session = get_object_or_404(AdmissionSession, pk=session_id)
        initial = {'capacity': session.default_slot_capacity}
        form = GenerateSlotsForm(request.POST or None, initial=initial)
        if request.method == 'POST' and form.is_valid():
            weekdays = [int(v) for v in form.cleaned_data['weekdays']]
            created, skipped = generate_slots(
                session,
                form.cleaned_data['start_date'],
                form.cleaned_data['end_date'],
                weekdays,
                capacity=form.cleaned_data['capacity'],
                skip_existing=form.cleaned_data['skip_existing'],
            )
            messages.success(
                request,
                f'Created {created} slots for {session.name} ({skipped} existing times skipped).',
            )
            return redirect('admin:admissions_vivaslot_changelist')
        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'session': session,
            'title': f'Auto-create viva slots — {session.name}',
            'default_times': session.default_slot_times,
        }
        return render(request, 'admin/admissions/generate_slots.html', context)


@admin.register(AdmissionClass)
class AdmissionClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'is_active', 'min_age_years', 'max_age_years', 'fee_override']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'code']


@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name']


@admin.register(VivaSlot)
class VivaSlotAdmin(admin.ModelAdmin):
    list_display = ['date', 'start_time', 'end_time', 'session', 'capacity', 'booked_count', 'remaining_display', 'is_active']
    list_filter = ['session', 'date', 'is_active']
    list_editable = ['capacity', 'is_active']
    date_hierarchy = 'date'
    search_fields = ['session__name']

    def remaining_display(self, obj):
        return obj.remaining
    remaining_display.short_description = 'Remaining'

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'form_number', 'student_name_en', 'admit_class', 'payment_status',
        'status', 'viva_slot', 'submitted_at', 'email_status',
    ]
    list_filter = ['status', 'payment_status', 'session', 'admit_class', 'needs_bus', 'financial_capacity']
    search_fields = [
        'form_number', 'student_name_en', 'student_name_bn', 'father_name',
        'mother_name', 'father_mobile', 'mother_mobile', 'birth_registration_no', 'email',
    ]
    readonly_fields = [
        'session', 'form_number', 'status', 'payment_status', 'access_token', 'resume_token',
        'wizard_step', 'student_name_en', 'student_name_bn', 'date_of_birth', 'age_years',
        'age_months', 'birth_registration_no', 'nationality', 'blood_group', 'gender',
        'present_division', 'present_zila', 'present_thana', 'present_address_line',
        'present_address', 'religion', 'photo', 'father_name', 'father_nid', 'father_occupation',
        'father_designation', 'father_organization', 'father_mobile',
        'father_division', 'father_zila', 'father_thana', 'father_address_line', 'father_address',
        'mother_name', 'mother_nid', 'mother_occupation', 'mother_designation',
        'mother_organization', 'mother_mobile',
        'mother_division', 'mother_zila', 'mother_thana', 'mother_address_line', 'mother_address', 'email',
        'family_income_yearly', 'earning_members', 'previous_school_name', 'needs_bus',
        'bus_stop', 'has_other_child', 'financial_capacity', 'agrees_uniform', 'agrees_rules',
        'info_correct', 'admit_class', 'viva_slot', 'slot_held_until', 'submitted_at',
        'paid_at', 'ip_address', 'form_pdf', 'confirmation_email_sent_at',
        'confirmation_email_error', 'created_at', 'updated_at',
    ]
    inlines = [PreviousResultInline, SiblingInline, PaymentAttemptInline]
    date_hierarchy = 'created_at'
    actions = ['export_excel', 'mark_paid_office', 'resend_confirmation', 'regenerate_pdf', 'cancel_selected']
    fieldsets = (
        ('Status', {
            'fields': (
                'form_number', 'session', 'admit_class', 'status', 'payment_status',
                'viva_slot', 'slot_held_until', 'submitted_at', 'paid_at',
            ),
        }),
        ('Student', {
            'fields': (
                'student_name_en', 'student_name_bn', 'date_of_birth', 'age_years', 'age_months',
                'birth_registration_no', 'nationality', 'blood_group', 'gender', 'religion',
                'present_division', 'present_zila', 'present_thana', 'present_address_line',
                'present_address', 'photo',
            ),
        }),
        ('Father', {
            'fields': (
                'father_name', 'father_nid', 'father_occupation', 'father_designation',
                'father_organization', 'father_mobile',
                'father_division', 'father_zila', 'father_thana', 'father_address_line',
                'father_address',
            ),
        }),
        ('Mother', {
            'fields': (
                'mother_name', 'mother_nid', 'mother_occupation', 'mother_designation',
                'mother_organization', 'mother_mobile',
                'mother_division', 'mother_zila', 'mother_thana', 'mother_address_line',
                'mother_address',
            ),
        }),
        ('Family & others', {
            'fields': (
                'email', 'family_income_yearly', 'earning_members', 'previous_school_name',
                'needs_bus', 'bus_stop', 'has_other_child',
                'financial_capacity', 'agrees_uniform', 'agrees_rules', 'info_correct',
            ),
        }),
        ('Files & email', {
            'fields': (
                'form_pdf', 'confirmation_email_sent_at', 'confirmation_email_error',
            ),
        }),
        ('Admin', {'fields': ('admin_notes', 'ip_address', 'created_at', 'updated_at')}),
    )

    def email_status(self, obj):
        if obj.confirmation_email_sent_at:
            return obj.confirmation_email_sent_at.strftime('%Y-%m-%d %H:%M')
        if obj.confirmation_email_error:
            return format_html('<span style="color:#b91c1c">Error</span>')
        return '—'
    email_status.short_description = 'Email'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == Application.Status.PAID:
            return False
        return super().has_delete_permission(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                'export-excel/',
                self.admin_site.admin_view(self.export_excel_view),
                name='admissions_application_export',
            ),
        ]
        return extra + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_url'] = reverse('admin:admissions_application_export')
        return super().changelist_view(request, extra_context=extra_context)

    def export_excel_view(self, request):
        cl = self.get_changelist_instance(request)
        qs = cl.get_queryset(request)
        output = applications_workbook(qs)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="admission-applications-{timezone.localdate()}.xlsx"'
        )
        return response

    @admin.action(description='Export selected to Excel')
    def export_excel(self, request, queryset):
        output = applications_workbook(queryset)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="admission-applications-{timezone.localdate()}.xlsx"'
        )
        return response

    @admin.action(description='Mark paid (office)')
    def mark_paid_office(self, request, queryset):
        count = 0
        for application in queryset.exclude(status=Application.Status.PAID):
            mark_application_paid(
                application,
                payment_status=Application.PaymentStatus.MANUAL,
                gateway='office',
            )
            count += 1
        self.message_user(request, f'Marked {count} application(s) as paid at the office.')

    @admin.action(description='Resend confirmation email')
    def resend_confirmation(self, request, queryset):
        sent = 0
        for application in queryset.filter(status=Application.Status.PAID):
            if send_confirmation_email(application, force=True, request=request):
                sent += 1
        self.message_user(request, f'Sent {sent} confirmation email(s).')

    @admin.action(description='Regenerate PDF')
    def regenerate_pdf(self, request, queryset):
        count = 0
        for application in queryset.filter(status=Application.Status.PAID):
            generate_and_store_pdf(application, force=True)
            count += 1
        self.message_user(request, f'Regenerated {count} PDF(s).')

    @admin.action(description='Cancel application')
    def cancel_selected(self, request, queryset):
        count = 0
        for application in queryset.exclude(status=Application.Status.CANCELLED):
            cancel_application(application)
            count += 1
        self.message_user(request, f'Cancelled {count} application(s).')


@admin.register(AdmissionSequence)
class AdmissionSequenceAdmin(admin.ModelAdmin):
    list_display = ['year', 'last_number']
