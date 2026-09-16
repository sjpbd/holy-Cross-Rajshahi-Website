# admissions/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from . import geo
from .constants import INPUT_CLASS, SELECT_CLASS, TEXTAREA_CLASS
from .models import AdmissionClass, Application, BusStop, PreviousResult, Sibling, VivaSlot
from .utils import birth_registration_warning, process_passport_photo, validate_bd_mobile, validate_nid

YES_NO = ((True, 'Yes'), (False, 'No'))


def coerce_bool(value):
    if value in (True, 'True', 'true', '1', 1):
        return True
    if value in (False, 'False', 'false', '0', 0):
        return False
    raise ValidationError('Please choose Yes or No.')


def _text(placeholder='', extra=None):
    attrs = {'class': INPUT_CLASS, 'placeholder': placeholder}
    if extra:
        attrs.update(extra)
    return forms.TextInput(attrs=attrs)


def _select():
    return forms.Select(attrs={'class': SELECT_CLASS})


def _textarea(placeholder='', rows=3):
    return forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': placeholder, 'rows': rows})


def _geo_choices(placeholder, names):
    return [('', placeholder)] + [(name, name) for name in names]


def bind_geo_fields(form, prefixes):
    divisions = _geo_choices('Select division', geo.divisions())
    zilas = _geo_choices('Select zila', geo.all_zilas())
    thanas = _geo_choices('Select thana', geo.all_thanas())
    for prefix in prefixes:
        form.fields[f'{prefix}_division'].choices = divisions
        form.fields[f'{prefix}_zila'].choices = zilas
        form.fields[f'{prefix}_thana'].choices = thanas
        form.fields[f'{prefix}_division'].required = True
        form.fields[f'{prefix}_zila'].required = True
        form.fields[f'{prefix}_thana'].required = True
        form.fields[f'{prefix}_address_line'].required = True
        form.fields[f'{prefix}_division'].widget = _select()
        form.fields[f'{prefix}_zila'].widget = _select()
        form.fields[f'{prefix}_thana'].widget = _select()
        form.fields[f'{prefix}_address_line'].widget = _text('House no., road, village or area')
        form.fields[f'{prefix}_division'].label = 'Division'
        form.fields[f'{prefix}_zila'].label = 'Zila'
        form.fields[f'{prefix}_thana'].label = 'Thana'
        form.fields[f'{prefix}_address_line'].label = 'Address'


def validate_geo_fields(cleaned, prefixes):
    errors = {}
    for prefix in prefixes:
        division = cleaned.get(f'{prefix}_division') or ''
        zila = cleaned.get(f'{prefix}_zila') or ''
        thana = cleaned.get(f'{prefix}_thana') or ''
        line = (cleaned.get(f'{prefix}_address_line') or '').strip()
        if line:
            cleaned[f'{prefix}_address_line'] = line
        if division and zila and zila not in geo.zilas(division):
            errors[f'{prefix}_zila'] = 'This zila does not belong to the selected division.'
        elif division and zila and thana and not geo.is_valid(division, zila, thana):
            errors[f'{prefix}_thana'] = 'This thana does not belong to the selected zila.'
        if not line:
            errors[f'{prefix}_address_line'] = 'Enter house, road, village, or area.'
    return errors


class StudentStepForm(forms.ModelForm):
    copy_same_permanent = forms.BooleanField(
        required=False,
        label='Permanent address is the same as present',
        widget=forms.CheckboxInput(attrs={
            '@change': "if ($event.target.checked) copy('present', 'permanent')",
        }),
    )

    class Meta:
        model = Application
        fields = [
            'admit_class',
            'student_name_en',
            'student_name_bn',
            'date_of_birth',
            'birth_registration_no',
            'nationality',
            'blood_group',
            'gender',
            'present_division',
            'present_zila',
            'present_thana',
            'present_address_line',
            'permanent_division',
            'permanent_zila',
            'permanent_thana',
            'permanent_address_line',
            'religion',
            'photo',
        ]
        widgets = {
            'admit_class': _select(),
            'student_name_en': _text('Student name in English'),
            'student_name_bn': _text('শিক্ষার্থীর নাম (বাংলা)'),
            'date_of_birth': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'birth_registration_no': _text('Birth registration number'),
            'nationality': _text(),
            'blood_group': _select(),
            'gender': _select(),
            'religion': _select(),
            'photo': forms.FileInput(attrs={
                'class': 'sr-only',
                'accept': 'image/jpeg,image/png',
                '@change': 'onPhoto($event)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bind_geo_fields(self, ['present', 'permanent'])
        copying = False
        if self.data:
            copying = self.data.get(self.add_prefix('copy_same_permanent')) in ('on', 'true', 'True', '1')
        elif self.instance.pk:
            present = self.instance.geo_payload('present')
            permanent = self.instance.geo_payload('permanent')
            copying = present == permanent and any(present.values())
        if copying:
            for name in ('permanent_division', 'permanent_zila', 'permanent_thana', 'permanent_address_line'):
                self.fields[name].required = False
        self.fields['admit_class'].queryset = AdmissionClass.objects.filter(is_active=True)
        self.fields['admit_class'].required = True
        self.fields['student_name_en'].required = True
        self.fields['student_name_bn'].required = True
        self.fields['date_of_birth'].required = True
        self.fields['birth_registration_no'].required = True
        self.fields['nationality'].required = True
        self.fields['blood_group'].required = True
        self.fields['gender'].required = True
        self.fields['religion'].required = True
        if not self.instance.photo:
            self.fields['photo'].required = True
        self.birth_reg_warning = ''
        self.fields['student_name_bn'].widget.attrs['class'] += ' font-bengali'
        if self.instance.pk:
            present = self.instance.geo_payload('present')
            permanent = self.instance.geo_payload('permanent')
            if present == permanent and any(present.values()):
                self.fields['copy_same_permanent'].initial = True

    def clean_birth_registration_no(self):
        value = (self.cleaned_data.get('birth_registration_no') or '').strip()
        self.birth_reg_warning = birth_registration_warning(value)
        return value

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            return photo
        if getattr(photo, 'closed', False):
            return photo
        # Skip reprocessing an already-saved file on the instance when unchanged
        if self.instance.pk and self.instance.photo and photo == self.instance.photo:
            return photo
        try:
            return process_passport_photo(photo, getattr(photo, 'name', None))
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError('Could not process the photo. Please upload a JPG or PNG.') from exc

    def clean(self):
        cleaned = super().clean()
        admit_class = cleaned.get('admit_class')
        dob = cleaned.get('date_of_birth')
        instance = self.instance
        if admit_class and dob and instance.session_id:
            instance.date_of_birth = dob
            instance.recompute_age()
            age = instance.age_years
            if age is not None:
                if admit_class.min_age_years is not None and age < admit_class.min_age_years:
                    raise ValidationError({
                        'date_of_birth': (
                            f'The minimum age for {admit_class.name} is {admit_class.min_age_years} years '
                            f'as of {instance.session.age_as_of_date:%d %B %Y}.'
                        ),
                    })
                if admit_class.max_age_years is not None and age > admit_class.max_age_years:
                    raise ValidationError({
                        'date_of_birth': (
                            f'The maximum age for {admit_class.name} is {admit_class.max_age_years} years '
                            f'as of {instance.session.age_as_of_date:%d %B %Y}.'
                        ),
                    })
        birth_reg = cleaned.get('birth_registration_no')
        if birth_reg and instance.session_id:
            clash = Application.objects.filter(
                session=instance.session,
                birth_registration_no=birth_reg,
            ).exclude(status__in=[Application.Status.CANCELLED, Application.Status.EXPIRED])
            if instance.pk:
                clash = clash.exclude(pk=instance.pk)
            if clash.exists():
                raise ValidationError({
                    'birth_registration_no': 'An application with this birth registration number already exists for this session.',
                })
        prefixes = ['present']
        if not cleaned.get('copy_same_permanent'):
            prefixes.append('permanent')
        geo_errors = validate_geo_fields(cleaned, prefixes)
        if geo_errors:
            raise ValidationError(geo_errors)
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('copy_same_permanent'):
            instance.copy_address('present', 'permanent')
        instance.sync_composed_addresses()
        if commit:
            instance.save()
        return instance


class FamilyStepForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            'father_name', 'father_nid', 'father_occupation', 'father_designation',
            'father_organization', 'father_mobile',
            'father_division', 'father_zila', 'father_thana', 'father_address_line',
            'mother_name', 'mother_nid', 'mother_occupation', 'mother_designation',
            'mother_organization', 'mother_mobile',
            'mother_division', 'mother_zila', 'mother_thana', 'mother_address_line',
            'email', 'family_income_yearly', 'earning_members', 'previous_school_name',
        ]
        widgets = {
            'father_name': _text("Father's name"),
            'father_nid': _text('Father NID'),
            'father_occupation': _text('Occupation'),
            'father_designation': _text('Designation'),
            'father_organization': _text('Organization / business name'),
            'father_mobile': _text('01XXXXXXXXX'),
            'mother_name': _text("Mother's name"),
            'mother_nid': _text('Mother NID'),
            'mother_occupation': _text('Occupation'),
            'mother_designation': _text('Designation'),
            'mother_organization': _text('Organization / business name'),
            'mother_mobile': _text('01XXXXXXXXX'),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Family email'}),
            'family_income_yearly': _select(),
            'earning_members': _text('Total earning members'),
            'previous_school_name': _text('Previous school (if any)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bind_geo_fields(self, ['father', 'mother'])
        self.fields['family_income_yearly'].choices = [
            ('', 'Select income range'),
        ] + list(Application.FamilyIncome.choices)
        for name in (
            'father_name', 'father_nid', 'father_occupation', 'father_mobile',
            'mother_name', 'mother_nid', 'mother_occupation', 'mother_mobile',
            'email', 'family_income_yearly', 'earning_members',
        ):
            self.fields[name].required = True

    def clean_father_nid(self):
        return validate_nid(self.cleaned_data.get('father_nid'))

    def clean_mother_nid(self):
        return validate_nid(self.cleaned_data.get('mother_nid'))

    def clean_father_mobile(self):
        return validate_bd_mobile(self.cleaned_data.get('father_mobile'))

    def clean_mother_mobile(self):
        value = self.cleaned_data.get('mother_mobile')
        if not value:
            return value
        return validate_bd_mobile(value)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('father_mobile') and not cleaned.get('mother_mobile'):
            raise ValidationError('Please provide at least one parent mobile number.')
        members = cleaned.get('earning_members')
        if members is not None and members < 0:
            raise ValidationError({'earning_members': 'Earning members cannot be negative.'})
        geo_errors = validate_geo_fields(cleaned, ['father', 'mother'])
        if geo_errors:
            raise ValidationError(geo_errors)
        return cleaned


class OthersStepForm(forms.ModelForm):
    needs_bus = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=forms.RadioSelect,
        label='Need bus from school for transport?',
    )
    has_other_child = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=forms.RadioSelect,
        label='Any other child in this school?',
    )
    class Meta:
        model = Application
        fields = ['needs_bus', 'bus_stop', 'has_other_child']
        widgets = {
            'bus_stop': _select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bus_stop'].queryset = BusStop.objects.filter(is_active=True)
        self.fields['bus_stop'].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('needs_bus') and not cleaned.get('bus_stop'):
            raise ValidationError({'bus_stop': 'Please select a bus stop.'})
        if not cleaned.get('needs_bus'):
            cleaned['bus_stop'] = None
        return cleaned


class DeclarationsStepForm(forms.ModelForm):
    financial_capacity = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=forms.RadioSelect,
        label='আর্থিক সামর্থ্য আছে কি / না?',
    )
    agrees_uniform = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=forms.RadioSelect,
        label='Uniform পরিধান করতে পারবে কি না?',
    )
    agrees_rules = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=forms.RadioSelect,
        label='স্কুলের সকল নিয়ম মেনে চলতে পারবে কি না?',
    )
    info_correct = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=forms.RadioSelect,
        label='All information on this form is correct.',
    )
    class Meta:
        model = Application
        fields = ['financial_capacity', 'agrees_uniform', 'agrees_rules', 'info_correct']
        widgets = {}
        labels = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('agrees_uniform') is not True:
            raise ValidationError({'agrees_uniform': 'You must be able to wear the school uniform to proceed.'})
        if cleaned.get('agrees_rules') is not True:
            raise ValidationError({'agrees_rules': 'You must agree to follow all school rules to proceed.'})
        if cleaned.get('info_correct') is not True:
            raise ValidationError({'info_correct': 'Please confirm that all information is correct.'})
        return cleaned


class PreviousResultForm(forms.ModelForm):
    class Meta:
        model = PreviousResult
        fields = ['previous_class', 'year', 'result']
        widgets = {
            'previous_class': _text('e.g. Class 5'),
            'year': _text('e.g. 2025'),
            'result': _text('GPA, division, or marks'),
        }
        labels = {
            'previous_class': 'Class',
            'year': 'Year',
            'result': 'Result',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['previous_class'].required = False
        self.fields['year'].required = False
        self.fields['result'].required = False
        self.fields['result'].help_text = ''

    def clean(self):
        cleaned = super().clean()
        previous_class = (cleaned.get('previous_class') or '').strip()
        year = (cleaned.get('year') or '').strip()
        result = (cleaned.get('result') or '').strip()
        cleaned['previous_class'] = previous_class
        cleaned['year'] = year
        cleaned['result'] = result
        return cleaned


def admission_class_choices():
    choices = [('', 'Select class')]
    seen = set()
    for klass in AdmissionClass.objects.filter(is_active=True).order_by('order', 'id'):
        if klass.name in seen:
            continue
        seen.add(klass.name)
        choices.append((klass.name, klass.name))
    return choices


class SiblingForm(forms.ModelForm):
    class Meta:
        model = Sibling
        fields = ['name', 'class_name']
        widgets = {
            'name': _text("Child's name"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = admission_class_choices()
        current = self.initial.get('class_name') or getattr(self.instance, 'class_name', '')
        if current and current not in dict(choices):
            choices.append((current, current))
        self.fields['name'].required = False
        self.fields['name'].label = "Child's name"
        self.fields['class_name'] = forms.ChoiceField(
            label='Class',
            required=False,
            choices=choices,
            widget=_select(),
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('DELETE'):
            return cleaned
        name = (cleaned.get('name') or '').strip()
        class_name = cleaned.get('class_name') or ''
        if name:
            cleaned['name'] = name
        if name and not class_name:
            self.add_error('class_name', 'Select a class.')
        if class_name and not name:
            self.add_error('name', 'Enter the child’s name.')
        return cleaned


PreviousResultFormSet = inlineformset_factory(
    Application,
    PreviousResult,
    form=PreviousResultForm,
    extra=1,
    can_delete=False,
    min_num=0,
    validate_min=False,
    max_num=8,
    validate_max=True,
)

SiblingFormSet = inlineformset_factory(
    Application,
    Sibling,
    form=SiblingForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=12,
    validate_max=True,
)


class ResumeForm(forms.Form):
    birth_registration_no = forms.CharField(
        label='Birth registration number',
        widget=_text('Birth registration number'),
    )
    father_mobile = forms.CharField(
        label="Father's mobile",
        widget=_text('01XXXXXXXXX'),
    )

    def clean_father_mobile(self):
        return validate_bd_mobile(self.cleaned_data.get('father_mobile'))


class LookupForm(forms.Form):
    form_number = forms.CharField(
        label='Form number',
        widget=_text('N-26-00001'),
    )
    father_mobile = forms.CharField(
        label="Father's mobile",
        widget=_text('01XXXXXXXXX'),
    )

    def clean_form_number(self):
        return (self.cleaned_data.get('form_number') or '').strip().upper()

    def clean_father_mobile(self):
        return validate_bd_mobile(self.cleaned_data.get('father_mobile'))


class SlotHoldForm(forms.Form):
    slot_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, session=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    def clean_slot_id(self):
        slot_id = self.cleaned_data['slot_id']
        qs = VivaSlot.objects.filter(pk=slot_id, is_active=True)
        if self.session:
            qs = qs.filter(session=self.session)
        slot = qs.first()
        if not slot:
            raise ValidationError('Please choose a valid viva slot.')
        return slot


class GenerateSlotsForm(forms.Form):
    WEEKDAY_CHOICES = [
        (6, 'Sunday'),
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
    ]
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}))
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        initial=['6', '0', '1', '2', '3'],
    )
    capacity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': INPUT_CLASS}))
    skip_existing = forms.BooleanField(required=False, initial=True, label='Skip dates/times that already have slots')

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            raise ValidationError('End date must be on or after the start date.')
        return cleaned
