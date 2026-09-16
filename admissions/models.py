# admissions/models.py
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


def default_slot_times():
    return [
        {'start': '09:00', 'end': '10:00'},
        {'start': '10:00', 'end': '11:00'},
        {'start': '11:00', 'end': '12:00'},
        {'start': '14:00', 'end': '15:00'},
    ]


def application_photo_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    token = instance.resume_token or uuid.uuid4()
    session_id = instance.session_id or 'na'
    return f'admission/photos/{session_id}/{token}.{ext}'


def application_pdf_path(instance, filename):
    name = instance.form_number or str(instance.resume_token or uuid.uuid4())
    session_id = instance.session_id or 'na'
    return f'admission/pdfs/{session_id}/{name}.pdf'


def signature_upload_path(instance, filename):
    return f'admission/signatures/{instance.pk or "session"}/{filename}'


class AdmissionSession(models.Model):
    """One admission circular (e.g. 2026–27). Only one may be marked open."""

    name = models.CharField(max_length=200, help_text="e.g. Admission 2026-27")
    academic_year = models.CharField(max_length=20, help_text="e.g. 2026-27")
    is_open = models.BooleanField(
        default=False,
        help_text="Only one session can be open. Apply is allowed only while this is on and now is inside the window.",
    )
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    age_as_of_date = models.DateField(
        help_text="Age is calculated as of this date (typically 1 January of the academic year).",
    )
    application_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Application fee in BDT. 0 until a payment gateway is connected.",
    )
    default_slot_capacity = models.PositiveIntegerField(
        default=20,
        help_text="N: maximum applicants per viva time slot unless a slot overrides this.",
    )
    slot_hold_minutes = models.PositiveIntegerField(
        default=15,
        help_text="How long a selected viva seat is reserved before payment.",
    )
    default_slot_times = models.JSONField(
        default=default_slot_times,
        help_text='List of {"start": "HH:MM", "end": "HH:MM"} used when auto-creating slots.',
    )
    principal_signature = models.ImageField(
        upload_to=signature_upload_path,
        blank=True,
        null=True,
        help_text="Shown on the viva admit card.",
    )
    viva_venue = models.CharField(
        max_length=300,
        blank=True,
        default='Holy Cross School & College, Rajshahi',
    )
    draft_expiry_days = models.PositiveIntegerField(default=14)
    instructions = models.TextField(
        blank=True,
        help_text="Shown on the public admission landing page.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-opens_at']
        verbose_name = 'Admission Session'
        verbose_name_plural = 'Admission Sessions'

    def __str__(self):
        status = 'Open' if self.is_open else 'Closed'
        return f'{self.name} ({status})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_open:
            AdmissionSession.objects.exclude(pk=self.pk).update(is_open=False)

    def is_currently_open(self):
        if not self.is_open:
            return False
        now = timezone.now()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        return True

    def year_prefix(self):
        digits = ''.join(ch for ch in self.academic_year if ch.isdigit())
        return digits[:4] if len(digits) >= 4 else str(timezone.localdate().year)

    @classmethod
    def get_open(cls):
        session = cls.objects.filter(is_open=True).first()
        if session and session.is_currently_open():
            return session
        return None


class AdmissionClass(models.Model):
    name = models.CharField(max_length=80)
    code = models.SlugField(max_length=20, unique=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    min_age_years = models.PositiveSmallIntegerField(blank=True, null=True)
    max_age_years = models.PositiveSmallIntegerField(blank=True, null=True)
    fee_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text='Leave blank to use the session fee.',
    )

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Admission Class'
        verbose_name_plural = 'Admission Classes'

    def __str__(self):
        return self.name


class BusStop(models.Model):
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Bus Stop'
        verbose_name_plural = 'Bus Stops'

    def __str__(self):
        return self.name


class VivaSlot(models.Model):
    session = models.ForeignKey(
        AdmissionSession,
        on_delete=models.CASCADE,
        related_name='viva_slots',
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    booked_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = [('session', 'date', 'start_time')]
        verbose_name = 'Viva Slot'
        verbose_name_plural = 'Viva Slots'

    def __str__(self):
        return f'{self.date} {self.start_time.strftime("%H:%M")}–{self.end_time.strftime("%H:%M")} ({self.booked_count}/{self.capacity})'

    @property
    def remaining(self):
        return max(0, self.capacity - self.booked_count)

    @property
    def is_full(self):
        return self.booked_count >= self.capacity

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})
        if self.pk and self.capacity < self.booked_count:
            raise ValidationError({
                'capacity': f'Capacity cannot be lower than current bookings ({self.booked_count}).',
            })
        if self.pk and not self.is_active:
            paid_exists = self.applications.filter(status=Application.Status.PAID).exists()
            if paid_exists:
                raise ValidationError({
                    'is_active': 'Cannot disable a slot that already has paid applications.',
                })

    def save(self, *args, **kwargs):
        releasing_holds = False
        if self.pk:
            previous = VivaSlot.objects.filter(pk=self.pk).values('is_active').first()
            if previous and previous['is_active'] and not self.is_active:
                releasing_holds = True
        super().save(*args, **kwargs)
        if releasing_holds:
            from .services import release_unpaid_holds_for_slot
            release_unpaid_holds_for_slot(self)


class AdmissionSequence(models.Model):
    year = models.CharField(max_length=4, unique=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.year}: {self.last_number}'


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting payment'
        PAID = 'paid', 'Paid'
        PAYMENT_FAILED = 'payment_failed', 'Payment failed'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        EXPIRED = 'expired', 'Expired'
        MANUAL = 'manual', 'Paid at office'

    class BloodGroup(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        UNKNOWN = 'Unknown', 'Unknown'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    class Religion(models.TextChoices):
        ISLAM = 'islam', 'Islam'
        HINDUISM = 'hinduism', 'Hinduism'
        CHRISTIANITY = 'christianity', 'Christianity'
        BUDDHISM = 'buddhism', 'Buddhism'
        OTHER = 'other', 'Other'

    session = models.ForeignKey(
        AdmissionSession,
        on_delete=models.PROTECT,
        related_name='applications',
    )
    admit_class = models.ForeignKey(
        AdmissionClass,
        on_delete=models.PROTECT,
        related_name='applications',
        null=True,
        blank=True,
    )
    form_number = models.CharField(max_length=32, blank=True, db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT, db_index=True)
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    resume_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    wizard_step = models.PositiveSmallIntegerField(default=1)

    student_name_en = models.CharField('Student name (English)', max_length=200, blank=True)
    student_name_bn = models.CharField('Student name (Bangla)', max_length=200, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    age_years = models.PositiveSmallIntegerField(blank=True, null=True)
    age_months = models.PositiveSmallIntegerField(blank=True, null=True)
    birth_registration_no = models.CharField(max_length=30, blank=True, db_index=True)
    nationality = models.CharField(max_length=80, blank=True, default='Bangladesh')
    blood_group = models.CharField(max_length=8, choices=BloodGroup.choices, blank=True)
    gender = models.CharField(max_length=16, choices=Gender.choices, blank=True)
    present_division = models.CharField('Present division', max_length=80, blank=True)
    present_zila = models.CharField('Present zila', max_length=80, blank=True)
    present_thana = models.CharField('Present thana', max_length=80, blank=True)
    present_address_line = models.CharField(
        'Present address',
        max_length=300,
        blank=True,
        help_text='House, road, village or area',
    )
    present_address = models.TextField(blank=True, help_text='Composed full present address')
    religion = models.CharField(max_length=20, choices=Religion.choices, blank=True)
    photo = models.ImageField(
        upload_to=application_photo_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
    )

    father_name = models.CharField(max_length=200, blank=True)
    father_nid = models.CharField(max_length=20, blank=True)
    father_occupation = models.CharField(max_length=120, blank=True)
    father_designation = models.CharField(max_length=120, blank=True)
    father_organization = models.CharField('Father organization / business', max_length=200, blank=True)
    father_mobile = models.CharField(max_length=20, blank=True)
    father_division = models.CharField("Father's division", max_length=80, blank=True)
    father_zila = models.CharField("Father's zila", max_length=80, blank=True)
    father_thana = models.CharField("Father's thana", max_length=80, blank=True)
    father_address_line = models.CharField("Father's address", max_length=300, blank=True)
    father_address = models.TextField(blank=True, help_text='Composed full father address')

    mother_name = models.CharField(max_length=200, blank=True)
    mother_nid = models.CharField(max_length=20, blank=True)
    mother_occupation = models.CharField(max_length=120, blank=True)
    mother_designation = models.CharField(max_length=120, blank=True)
    mother_organization = models.CharField('Mother organization / business', max_length=200, blank=True)
    mother_mobile = models.CharField(max_length=20, blank=True)
    mother_division = models.CharField("Mother's division", max_length=80, blank=True)
    mother_zila = models.CharField("Mother's zila", max_length=80, blank=True)
    mother_thana = models.CharField("Mother's thana", max_length=80, blank=True)
    mother_address_line = models.CharField("Mother's address", max_length=300, blank=True)
    mother_address = models.TextField(blank=True, help_text='Composed full mother address')

    email = models.EmailField(blank=True)
    family_income_yearly = models.PositiveIntegerField(
        'Family income (yearly, BDT)',
        blank=True,
        null=True,
    )
    earning_members = models.PositiveSmallIntegerField(blank=True, null=True)
    previous_school_name = models.CharField(max_length=200, blank=True)

    needs_bus = models.BooleanField(default=False)
    bus_stop = models.ForeignKey(
        BusStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
    )
    has_other_child = models.BooleanField(default=False)

    financial_capacity = models.BooleanField(
        'Has financial capacity',
        null=True,
        blank=True,
        help_text='Yes / No — No is allowed but flagged for admin.',
    )
    agrees_uniform = models.BooleanField(null=True, blank=True)
    agrees_rules = models.BooleanField(null=True, blank=True)
    info_correct = models.BooleanField(null=True, blank=True)

    viva_slot = models.ForeignKey(
        VivaSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
    )
    slot_held_until = models.DateTimeField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    form_pdf = models.FileField(upload_to=application_pdf_path, blank=True, null=True)
    confirmation_email_sent_at = models.DateTimeField(blank=True, null=True)
    confirmation_email_error = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'birth_registration_no'],
                condition=(
                    ~Q(status__in=['cancelled', 'expired'])
                    & ~Q(birth_registration_no='')
                ),
                name='uniq_live_birth_reg_per_session',
            ),
        ]

    def __str__(self):
        name = self.student_name_en or 'Draft'
        return f'{self.form_number or "—"} · {name}'

    @property
    def contact_number(self):
        return self.father_mobile or self.mother_mobile or ''

    @property
    def is_paid(self):
        return self.status == self.Status.PAID and self.payment_status in (
            self.PaymentStatus.PAID,
            self.PaymentStatus.MANUAL,
        )

    @property
    def hold_is_valid(self):
        return bool(
            self.viva_slot_id
            and self.slot_held_until
            and self.slot_held_until > timezone.now()
        )

    def fee_amount(self):
        if self.admit_class and self.admit_class.fee_override is not None:
            return self.admit_class.fee_override
        return self.session.application_fee

    def recompute_age(self):
        if not self.date_of_birth or not self.session_id:
            self.age_years = None
            self.age_months = None
            return
        as_of = self.session.age_as_of_date
        years = as_of.year - self.date_of_birth.year
        months = as_of.month - self.date_of_birth.month
        if as_of.day < self.date_of_birth.day:
            months -= 1
        if months < 0:
            years -= 1
            months += 12
        self.age_years = max(0, years)
        self.age_months = months

    def geo_payload(self, prefix):
        return {
            'division': getattr(self, f'{prefix}_division', '') or '',
            'zila': getattr(self, f'{prefix}_zila', '') or '',
            'thana': getattr(self, f'{prefix}_thana', '') or '',
            'line': getattr(self, f'{prefix}_address_line', '') or '',
        }

    def copy_address(self, source='present', dest='father'):
        for part in ('division', 'zila', 'thana', 'address_line'):
            setattr(self, f'{dest}_{part}', getattr(self, f'{source}_{part}', '') or '')
        self.sync_composed_addresses()

    def sync_composed_addresses(self):
        from .geo import compose
        self.present_address = compose(
            self.present_division, self.present_zila, self.present_thana, self.present_address_line,
        )
        self.father_address = compose(
            self.father_division, self.father_zila, self.father_thana, self.father_address_line,
        )
        self.mother_address = compose(
            self.mother_division, self.mother_zila, self.mother_thana, self.mother_address_line,
        )

    def save(self, *args, **kwargs):
        if self.date_of_birth and self.session_id:
            self.recompute_age()
        self.sync_composed_addresses()
        super().save(*args, **kwargs)


class PreviousResult(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='previous_results',
    )
    previous_class = models.CharField('Class', max_length=80, blank=True)
    year = models.CharField(max_length=10, blank=True)
    result = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.previous_class} ({self.result})'

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.previous_class} ({self.result})'


class Sibling(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='siblings',
    )
    name = models.CharField("Child's name", max_length=200)
    class_name = models.CharField('Class', max_length=80)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.name} — {self.class_name}'


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        STARTED = 'started', 'Started'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        EXPIRED = 'expired', 'Expired'

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='payment_attempts',
    )
    gateway = models.CharField(max_length=40, default='stub')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=120, blank=True, db_index=True)
    raw_payload = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.STARTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.application} · {self.status} · {self.amount}'
