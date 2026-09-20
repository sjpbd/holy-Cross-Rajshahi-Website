# admissions/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from . import geo
from .constants import (
    CLASS_6_REG_CODES,
    CLASS_8_REG_CODES,
    INPUT_CLASS,
    SELECT_CLASS,
    SIBLING_CLASS_NAMES,
    STUDY_GROUP_CODES,
    TEXTAREA_CLASS,
)
from .models import AdmissionClass, Application, BusStop, PreviousResult, Sibling, VivaSlot
from .utils import (
    process_passport_photo,
    validate_bd_mobile,
    validate_bengali_text,
    validate_birth_registration,
    validate_nid,
)

YES_NO = ((True, 'Yes'), (False, 'No'))
PHONE_EXTRA = {'inputmode': 'numeric', 'autocomplete': 'tel', 'data-validate': 'phone'}
BIRTH_EXTRA = {'inputmode': 'numeric', 'data-validate': 'birth'}
BENGALI_EXTRA = {'data-validate': 'bengali', 'lang': 'bn'}


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


def _radios():
    return forms.RadioSelect(attrs={'class': 'adm-radios'})


def _geo_choices(placeholder, names):
    return [('', placeholder)] + [(name, name) for name in names]


def _mark_required_widgets(form):
    for field in form.fields.values():
        if field.required and not isinstance(field.widget, forms.RadioSelect):
            field.widget.attrs['data-required'] = 'true'


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
            'hobby',
            'other_skills',
            'class_6_reg_no',
            'class_8_reg_no',
            'study_group',
            'photo',
        ]
        widgets = {
            'admit_class': _select(),
            'student_name_en': _text('Student name in English'),
            'student_name_bn': _text('শিক্ষার্থীর নাম (বাংলা)', extra=BENGALI_EXTRA),
            'date_of_birth': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'birth_registration_no': _text('13, 16, or 17 digits', extra=BIRTH_EXTRA),
            'nationality': _text(),
            'blood_group': _select(),
            'gender': _select(),
            'religion': _select(),
            'hobby': _text('Hobby (optional)'),
            'other_skills': _text('Any other skills (optional)'),
            'class_6_reg_no': _text('Class 6 registration number'),
            'class_8_reg_no': _text('Class 8 registration number'),
            'study_group': _select(),
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
        self.fields['birth_registration_no'].help_text = 'Must be 13, 16, or 17 digits.'
        self.fields['nationality'].required = True
        self.fields['blood_group'].required = True
        self.fields['blood_group'].choices = [('', 'Select blood group')] + list(Application.BloodGroup.choices)
        self.fields['gender'].required = True
        self.fields['religion'].required = True
        self.fields['hobby'].required = False
        self.fields['other_skills'].required = False
        self.fields['class_6_reg_no'].required = False
        self.fields['class_8_reg_no'].required = False
        self.fields['study_group'].required = False
        self.fields['study_group'].choices = [('', 'Select group')] + list(Application.StudyGroup.choices)
        if not self.instance.photo:
            self.fields['photo'].required = True
        self.fields['student_name_bn'].widget.attrs['class'] += ' font-bengali'
        self.fields['student_name_bn'].help_text = 'শুধু বাংলা অক্ষরে লিখুন.'
        if self.instance.pk:
            present = self.instance.geo_payload('present')
            permanent = self.instance.geo_payload('permanent')
            if present == permanent and any(present.values()):
                self.fields['copy_same_permanent'].initial = True
        _mark_required_widgets(self)

    def clean_student_name_bn(self):
        return validate_bengali_text(self.cleaned_data.get('student_name_bn'))

    def clean_birth_registration_no(self):
        return validate_birth_registration(self.cleaned_data.get('birth_registration_no'))

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            return photo
        if getattr(photo, 'closed', False):
            return photo
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
        code = (admit_class.code if admit_class else '') or ''
        errors = {}
        class_6 = (cleaned.get('class_6_reg_no') or '').strip()
        class_8 = (cleaned.get('class_8_reg_no') or '').strip()
        group = cleaned.get('study_group') or ''
        cleaned['class_6_reg_no'] = class_6
        cleaned['class_8_reg_no'] = class_8
        if code not in CLASS_6_REG_CODES:
            cleaned['class_6_reg_no'] = ''
        elif not class_6:
            errors['class_6_reg_no'] = 'Enter the Class 6 registration number.'
        if code not in CLASS_8_REG_CODES:
            cleaned['class_8_reg_no'] = ''
        elif not class_8:
            errors['class_8_reg_no'] = 'Enter the Class 8 registration number.'
        if code not in STUDY_GROUP_CODES:
            cleaned['study_group'] = ''
        elif not group:
            errors['study_group'] = 'Select Science or Commerce.'
        prefixes = ['present']
        if not cleaned.get('copy_same_permanent'):
            prefixes.append('permanent')
        errors.update(validate_geo_fields(cleaned, prefixes))
        if errors:
            raise ValidationError(errors)
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
            'father_name', 'father_name_bn', 'father_nid', 'father_occupation', 'father_designation',
            'father_organization', 'father_mobile',
            'father_division', 'father_zila', 'father_thana', 'father_address_line',
            'mother_name', 'mother_name_bn', 'mother_nid', 'mother_occupation', 'mother_designation',
            'mother_organization', 'mother_mobile',
            'mother_division', 'mother_zila', 'mother_thana', 'mother_address_line',
            'whatsapp_number', 'guardian_type', 'guardian_name', 'guardian_relation', 'guardian_phone',
            'email', 'family_income_yearly', 'earning_members', 'previous_school_name',
        ]
        widgets = {
            'father_name': _text("Father's name"),
            'father_name_bn': _text('বাবার নাম (বাংলা)', extra=BENGALI_EXTRA),
            'father_nid': _text('Father NID'),
            'father_occupation': _text('Occupation'),
            'father_designation': _text('Designation'),
            'father_organization': _text('Organization / business name'),
            'father_mobile': _text('01XXXXXXXXX', extra=PHONE_EXTRA),
            'mother_name': _text("Mother's name"),
            'mother_name_bn': _text('মায়ের নাম (বাংলা)', extra=BENGALI_EXTRA),
            'mother_nid': _text('Mother NID'),
            'mother_occupation': _text('Occupation'),
            'mother_designation': _text('Designation'),
            'mother_organization': _text('Organization / business name'),
            'mother_mobile': _text('01XXXXXXXXX', extra=PHONE_EXTRA),
            'whatsapp_number': _text('01XXXXXXXXX', extra=PHONE_EXTRA),
            'guardian_type': _radios(),
            'guardian_name': _text('Guardian’s full name'),
            'guardian_relation': _text('Uncle, aunt, grandfather…'),
            'guardian_phone': _text('01XXXXXXXXX', extra=PHONE_EXTRA),
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
        self.fields['guardian_type'].choices = Application.GuardianType.choices
        self.fields['guardian_type'].label = 'Guardian is'
        self.fields['whatsapp_number'].help_text = (
            'Must be correct. All information will be sent to this WhatsApp number.'
        )
        self.fields['father_name_bn'].widget.attrs['class'] += ' font-bengali'
        self.fields['mother_name_bn'].widget.attrs['class'] += ' font-bengali'
        self.fields['father_mobile'].help_text = 'Must be 11 digits (01XXXXXXXXX).'
        self.fields['mother_mobile'].help_text = 'Must be 11 digits (01XXXXXXXXX).'
        for name in (
            'father_name', 'father_name_bn', 'father_nid', 'father_occupation', 'father_mobile',
            'mother_name', 'mother_name_bn', 'mother_nid', 'mother_occupation', 'mother_mobile',
            'whatsapp_number', 'guardian_type',
            'email', 'family_income_yearly', 'earning_members',
        ):
            self.fields[name].required = True
        self.fields['guardian_name'].required = False
        self.fields['guardian_relation'].required = False
        self.fields['guardian_phone'].required = False
        self.fields['guardian_phone'].help_text = 'Must be 11 digits (01XXXXXXXXX).'
        self.fields['guardian_name'].widget.attrs['data-required'] = 'true'
        self.fields['guardian_relation'].widget.attrs['data-required'] = 'true'
        self.fields['guardian_phone'].widget.attrs['data-required'] = 'true'
        _mark_required_widgets(self)

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

    def clean_whatsapp_number(self):
        return validate_bd_mobile(self.cleaned_data.get('whatsapp_number'))

    def clean_guardian_phone(self):
        value = self.cleaned_data.get('guardian_phone')
        if not value:
            return ''
        return validate_bd_mobile(value)

    def clean_father_name_bn(self):
        return validate_bengali_text(self.cleaned_data.get('father_name_bn'))

    def clean_mother_name_bn(self):
        return validate_bengali_text(self.cleaned_data.get('mother_name_bn'))

    def clean(self):
        cleaned = super().clean()
        errors = {}
        if not cleaned.get('father_mobile') and not cleaned.get('mother_mobile'):
            errors['__all__'] = 'Please provide at least one parent mobile number.'
        members = cleaned.get('earning_members')
        if members is not None and members < 0:
            errors['earning_members'] = 'Earning members cannot be negative.'
        if self.instance.is_nursery:
            cleaned['previous_school_name'] = ''
        guardian_type = cleaned.get('guardian_type')
        if guardian_type == Application.GuardianType.FATHER:
            if not (cleaned.get('father_name') or '').strip():
                errors['guardian_type'] = 'Enter the father’s name above first.'
            cleaned['guardian_name'] = (cleaned.get('father_name') or '').strip()
            cleaned['guardian_relation'] = 'Father'
            cleaned['guardian_phone'] = (cleaned.get('father_mobile') or '').strip()
        elif guardian_type == Application.GuardianType.MOTHER:
            if not (cleaned.get('mother_name') or '').strip():
                errors['guardian_type'] = 'Enter the mother’s name above first.'
            cleaned['guardian_name'] = (cleaned.get('mother_name') or '').strip()
            cleaned['guardian_relation'] = 'Mother'
            cleaned['guardian_phone'] = (cleaned.get('mother_mobile') or '').strip()
        elif guardian_type == Application.GuardianType.OTHER:
            if not (cleaned.get('guardian_name') or '').strip():
                errors['guardian_name'] = 'Enter the guardian’s name.'
            if not (cleaned.get('guardian_relation') or '').strip():
                errors['guardian_relation'] = 'Enter the relation to the student.'
            if not (cleaned.get('guardian_phone') or '').strip():
                errors['guardian_phone'] = 'Enter the guardian’s phone number.'
        elif not guardian_type:
            errors['guardian_type'] = 'Select father, mother, or another person.'
        geo_errors = validate_geo_fields(cleaned, ['father', 'mother'])
        errors.update(geo_errors)
        if errors:
            raise ValidationError(errors)
        return cleaned


class OthersStepForm(forms.ModelForm):
    needs_bus = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=_radios(),
        label='Need bus from school for transport?',
    )
    has_other_child = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=_radios(),
        label='Any other child in this school?',
    )

    class Meta:
        model = Application
        fields = ['needs_bus', 'bus_start_stop', 'bus_end_stop', 'has_other_child']
        widgets = {
            'bus_start_stop': _select(),
            'bus_end_stop': _select(),
        }
        labels = {
            'bus_start_stop': 'Starting stop',
            'bus_end_stop': 'Ending stop',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stops = BusStop.objects.filter(is_active=True)
        self.fields['bus_start_stop'].queryset = stops
        self.fields['bus_end_stop'].queryset = stops
        self.fields['bus_start_stop'].required = False
        self.fields['bus_end_stop'].required = False
        _mark_required_widgets(self)

    def clean(self):
        cleaned = super().clean()
        errors = {}
        if cleaned.get('needs_bus'):
            if not cleaned.get('bus_start_stop'):
                errors['bus_start_stop'] = 'Please select a starting stop.'
            if not cleaned.get('bus_end_stop'):
                errors['bus_end_stop'] = 'Please select an ending stop.'
        else:
            cleaned['bus_start_stop'] = None
            cleaned['bus_end_stop'] = None
        if errors:
            raise ValidationError(errors)
        return cleaned


class DeclarationsStepForm(forms.ModelForm):
    financial_capacity = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=_radios(),
        label='আর্থিক সামর্থ্য আছে কি / না?',
    )
    agrees_uniform = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=_radios(),
        label='Uniform পরিধান করতে পারবে কি না?',
    )
    agrees_rules = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=_radios(),
        label='স্কুলের সকল নিয়ম মেনে চলতে পারবে কি না?',
    )
    info_correct = forms.TypedChoiceField(
        choices=YES_NO,
        coerce=coerce_bool,
        widget=_radios(),
        label='All information on this form is correct.',
    )

    class Meta:
        model = Application
        fields = ['financial_capacity', 'agrees_uniform', 'agrees_rules', 'info_correct']
        widgets = {}
        labels = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _mark_required_widgets(self)

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
    for klass in AdmissionClass.objects.all().order_by('order', 'id'):
        if klass.name in seen:
            continue
        seen.add(klass.name)
        choices.append((klass.name, klass.name))
    for name in SIBLING_CLASS_NAMES:
        if name not in seen:
            seen.add(name)
            choices.append((name, name))
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
        widget=_text('Birth registration number', extra=BIRTH_EXTRA),
        help_text='Must be 13, 16, or 17 digits.',
    )
    father_mobile = forms.CharField(
        label="Father's mobile",
        widget=_text('01XXXXXXXXX', extra=PHONE_EXTRA),
        help_text='Must be 11 digits (01XXXXXXXXX).',
    )

    def clean_birth_registration_no(self):
        return validate_birth_registration(self.cleaned_data.get('birth_registration_no'))

    def clean_father_mobile(self):
        return validate_bd_mobile(self.cleaned_data.get('father_mobile'))


class LookupForm(forms.Form):
    form_number = forms.CharField(
        label='Application No',
        widget=_text('N-26-00001'),
    )
    father_mobile = forms.CharField(
        label="Father's mobile",
        widget=_text('01XXXXXXXXX', extra=PHONE_EXTRA),
        help_text='Must be 11 digits (01XXXXXXXXX).',
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
