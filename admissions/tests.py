# admissions/tests.py
import os
from datetime import date, time, timedelta
from io import BytesIO
from unittest.mock import patch

from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .constants import RESUME_COOKIE
from .excel import sanitize_excel
from .models import (
    AdmissionClass,
    AdmissionSequence,
    AdmissionSession,
    Application,
    BusStop,
    VivaSlot,
)
from .payments import StubPaymentGateway
from .services import (
    SlotUnavailable,
    assign_form_number,
    expire_slot_holds,
    hold_slot,
    mark_application_paid,
)
from .utils import should_skip_cache


def make_photo_file(name='photo.jpg'):
    img = Image.frombytes('RGB', (400, 500), os.urandom(400 * 500 * 3))
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')


def fake_store_pdf(application, force=False):
    application.form_pdf.save('form.pdf', ContentFile(b'%PDF-fake'), save=True)
    return application


class AdmissionBaseTestCase(TestCase):
    def setUp(self):
        AdmissionSession.objects.update(is_open=False)
        now = timezone.now()
        self.session = AdmissionSession.objects.create(
            name='Admission 2026-27',
            academic_year='2026-27',
            is_open=True,
            opens_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=60),
            age_as_of_date=date(2026, 1, 1),
            application_fee=500,
            default_slot_capacity=2,
            slot_hold_minutes=15,
        )
        self.klass = AdmissionClass.objects.create(
            name='Class 1',
            code='c1-test',
            is_active=True,
            min_age_years=5,
            max_age_years=8,
        )
        self.stop = BusStop.objects.create(name='Court Station', is_active=True)
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.slot = VivaSlot.objects.create(
            session=self.session,
            date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=2,
        )

    def student_payload(self, **overrides):
        data = {
            'admit_class': self.klass.pk,
            'student_name_en': 'Rahim Ali',
            'student_name_bn': 'রহিম আলী',
            'date_of_birth': '2018-06-15',
            'birth_registration_no': '19901234567890123',
            'nationality': 'Bangladesh',
            'blood_group': 'A+',
            'gender': 'male',
            'present_division': 'Rajshahi',
            'present_zila': 'Rajshahi',
            'present_thana': 'Boalia',
            'present_address_line': 'House 12, Sagorpara',
            'copy_same_permanent': 'on',
            'religion': 'islam',
        }
        data.update(overrides)
        return data

    def family_payload(self, **overrides):
        data = {
            'father_name': 'Karim Ali',
            'father_name_bn': 'করিম আলী',
            'father_nid': '1234567890',
            'father_occupation': 'Teacher',
            'father_designation': '',
            'father_organization': 'School',
            'father_mobile': '01711111111',
            'father_division': 'Rajshahi',
            'father_zila': 'Rajshahi',
            'father_thana': 'Boalia',
            'father_address_line': 'House 12, Sagorpara',
            'mother_name': 'Fatema',
            'mother_name_bn': 'ফাতেমা',
            'mother_nid': '0987654321',
            'mother_occupation': 'Homemaker',
            'mother_designation': '',
            'mother_organization': '',
            'mother_mobile': '01811111111',
            'mother_division': 'Rajshahi',
            'mother_zila': 'Rajshahi',
            'mother_thana': 'Boalia',
            'mother_address_line': 'House 12, Sagorpara',
            'whatsapp_number': '01711111111',
            'guardian_type': Application.GuardianType.FATHER,
            'guardian_name': '',
            'guardian_relation': '',
            'guardian_phone': '',
            'email': 'parent@example.com',
            'family_income_yearly': Application.FamilyIncome.ABOVE_200,
            'earning_members': '1',
            'previous_school_name': '',
            'results-TOTAL_FORMS': '1',
            'results-INITIAL_FORMS': '0',
            'results-MIN_NUM_FORMS': '0',
            'results-MAX_NUM_FORMS': '8',
            'results-0-previous_class': '',
            'results-0-year': '',
            'results-0-result': '',
        }
        data.update(overrides)
        return data

    def make_application(self, **kwargs):
        data = {
            'session': self.session,
            'admit_class': self.klass,
            'student_name_en': 'Rahim Ali',
            'student_name_bn': 'রহিম আলী',
            'date_of_birth': date(2018, 6, 15),
            'birth_registration_no': kwargs.pop('birth_registration_no', '19901234567890123'),
            'nationality': 'Bangladesh',
            'blood_group': 'A+',
            'gender': Application.Gender.MALE,
            'present_address': 'Rajshahi',
            'present_division': 'Rajshahi',
            'present_zila': 'Rajshahi',
            'present_thana': 'Boalia',
            'present_address_line': 'House 12, Sagorpara',
            'permanent_division': 'Rajshahi',
            'permanent_zila': 'Rajshahi',
            'permanent_thana': 'Boalia',
            'permanent_address_line': 'House 12, Sagorpara',
            'religion': Application.Religion.ISLAM,
            'father_name': 'Karim Ali',
            'father_name_bn': 'করিম আলী',
            'father_nid': '1234567890',
            'father_occupation': 'Teacher',
            'father_mobile': '01711111111',
            'father_address': 'Rajshahi',
            'father_division': 'Rajshahi',
            'father_zila': 'Rajshahi',
            'father_thana': 'Boalia',
            'father_address_line': 'House 12, Sagorpara',
            'mother_name': 'Fatema',
            'mother_name_bn': 'ফাতেমা',
            'mother_nid': '0987654321',
            'mother_occupation': 'Homemaker',
            'mother_mobile': '01811111111',
            'mother_address': 'Rajshahi',
            'mother_division': 'Rajshahi',
            'mother_zila': 'Rajshahi',
            'mother_thana': 'Boalia',
            'mother_address_line': 'House 12, Sagorpara',
            'whatsapp_number': '01711111111',
            'guardian_type': Application.GuardianType.FATHER,
            'guardian_name': 'Karim Ali',
            'guardian_relation': 'Father',
            'guardian_phone': '01711111111',
            'email': 'parent@example.com',
            'family_income_yearly': Application.FamilyIncome.ABOVE_200,
            'earning_members': 1,
            'agrees_uniform': True,
            'agrees_rules': True,
            'info_correct': True,
            'financial_capacity': True,
        }
        data.update(kwargs)
        return Application.objects.create(**data)


class AgeAndDuplicateTests(AdmissionBaseTestCase):
    def test_age_as_of_session_date(self):
        app = self.make_application(date_of_birth=date(2018, 6, 15))
        self.assertEqual(app.age_years, 7)
        self.assertEqual(app.age_months, 6)

    def test_class_min_age_blocks(self):
        photo = make_photo_file()
        self.client.get(reverse('admissions:apply'))
        response = self.client.post(reverse('admissions:apply') + '?step=1', self.student_payload(
            student_name_en='Too Young',
            student_name_bn='ছোট',
            date_of_birth='2022-06-15',
            birth_registration_no='19901234567890999',
            present_address_line='House 1',
            photo=photo,
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'minimum age')

    def test_duplicate_birth_registration(self):
        self.make_application(birth_registration_no='19901234567890111')
        photo = make_photo_file()
        self.client.get(reverse('admissions:apply'))
        response = self.client.post(reverse('admissions:apply') + '?step=1', self.student_payload(
            student_name_en='Other Child',
            student_name_bn='অন্য',
            date_of_birth='2018-01-01',
            birth_registration_no='19901234567890111',
            blood_group='B+',
            present_address_line='House 2',
            photo=photo,
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')


class SlotTests(AdmissionBaseTestCase):
    def test_last_seat_race(self):
        self.slot.capacity = 1
        self.slot.save()
        first = self.make_application(birth_registration_no='19901234567890001')
        second = self.make_application(birth_registration_no='19901234567890002')
        hold_slot(first, self.slot)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.booked_count, 1)
        with self.assertRaises(SlotUnavailable):
            hold_slot(second, self.slot)

    def test_hold_expiry_releases_seat(self):
        app = self.make_application()
        hold_slot(app, self.slot)
        app.slot_held_until = timezone.now() - timedelta(minutes=1)
        app.status = Application.Status.AWAITING_PAYMENT
        app.save(update_fields=['slot_held_until', 'status'])
        expire_slot_holds()
        self.slot.refresh_from_db()
        app.refresh_from_db()
        self.assertEqual(self.slot.booked_count, 0)
        self.assertIsNone(app.viva_slot_id)
        self.assertEqual(app.status, Application.Status.DRAFT)

    def test_form_number_assigned_once(self):
        app = self.make_application()
        first = assign_form_number(app)
        second = assign_form_number(app)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith('1-26-'))
        self.assertEqual(AdmissionSequence.objects.get(year='2026', class_code='1').last_number, 1)

    def test_nursery_form_number_format(self):
        nursery = AdmissionClass.objects.create(
            name='Nursery', code='n-test', form_code='N', is_active=True,
        )
        app = self.make_application(admit_class=nursery, birth_registration_no='19901234567890911')
        self.assertEqual(assign_form_number(app), 'N-26-00001')


class PaymentPdfEmailTests(AdmissionBaseTestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('admissions.pdf.generate_and_store_pdf', side_effect=fake_store_pdf)
    def test_email_sent_once_on_paid(self, _pdf):
        app = self.make_application()
        hold_slot(app, self.slot)
        mark_application_paid(app)
        mark_application_paid(app)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(app.form_number, mail.outbox[0].subject)
        self.assertTrue(mail.outbox[0].attachments)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('admissions.pdf.generate_and_store_pdf', side_effect=fake_store_pdf)
    def test_duplicate_ipn_does_not_resend(self, _pdf):
        app = self.make_application()
        hold_slot(app, self.slot)
        factory = RequestFactory()
        gateway = StubPaymentGateway()
        request = factory.post('/admission/payment/ipn/', {
            'application_token': str(app.access_token),
            'status': 'success',
            'tran_id': 'abc-1',
        })
        gateway.handle_ipn(request)
        gateway.handle_ipn(request)
        self.assertEqual(len(mail.outbox), 1)
        app.refresh_from_db()
        self.assertTrue(app.is_paid)

    @patch('admissions.pdf.generate_and_store_pdf', side_effect=fake_store_pdf)
    def test_email_failure_leaves_application_paid(self, _pdf):
        from admissions.emails import send_confirmation_email

        app = self.make_application()
        hold_slot(app, self.slot)
        app.status = Application.Status.PAID
        app.payment_status = Application.PaymentStatus.PAID
        assign_form_number(app)
        fake_store_pdf(app)
        app.save()

        with patch('admissions.emails.EmailMultiAlternatives.send', side_effect=RuntimeError('smtp down')):
            ok = send_confirmation_email(app)
        app.refresh_from_db()
        self.assertFalse(ok)
        self.assertTrue(app.is_paid)
        self.assertIn('smtp down', app.confirmation_email_error)

    def test_pdf_forbidden_unless_paid(self):
        app = self.make_application()
        url = reverse('admissions:pdf_download', kwargs={'token': app.access_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_paid_download_works(self):
        app = self.make_application()
        app.status = Application.Status.PAID
        app.payment_status = Application.PaymentStatus.PAID
        fake_store_pdf(app)
        app.save()
        url = reverse('admissions:pdf_download', kwargs={'token': app.access_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')


class SessionAndCacheTests(AdmissionBaseTestCase):
    def test_closed_session_blocks_apply(self):
        self.session.is_open = False
        self.session.save()
        response = self.client.get(reverse('admissions:apply'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admissions:landing'))

    def test_cache_skip_prefixes(self):
        factory = RequestFactory()
        self.assertTrue(should_skip_cache(factory.get('/admission/')))
        self.assertTrue(should_skip_cache(factory.get('/admission/apply/')))
        self.assertTrue(should_skip_cache(factory.get('/admin/')))
        self.assertTrue(should_skip_cache(factory.get('/contact/')))
        self.assertFalse(should_skip_cache(factory.get('/')))
        self.assertFalse(should_skip_cache(factory.get('/notices/')))

    def test_admission_get_is_not_cached(self):
        response = self.client.get(reverse('admissions:landing'))
        self.assertEqual(response.status_code, 200)
        cache_control = response.get('Cache-Control', '')
        self.assertTrue('no-cache' in cache_control or 'private' in cache_control or should_skip_cache(response.wsgi_request))

    def test_excel_sanitization(self):
        self.assertEqual(sanitize_excel('=CMD()'), "'=CMD()")
        self.assertEqual(sanitize_excel('+1+1'), "'+1+1")
        self.assertEqual(sanitize_excel('-total'), "'-total")
        self.assertEqual(sanitize_excel('@sum'), "'@sum")
        self.assertEqual(sanitize_excel('Rahim'), 'Rahim')
        self.assertEqual(sanitize_excel(True), 'Yes')


class WizardFlowTests(AdmissionBaseTestCase):
    def test_full_apply_to_paid_pdf(self):
        apply = reverse('admissions:apply')
        self.client.get(apply)
        photo = make_photo_file()
        response = self.client.post(apply + '?step=1', self.student_payload(photo=photo))
        if response.status_code != 302:
            form = response.context['form'] if response.context else None
            self.fail(f'step1 status={response.status_code} errors={getattr(form, "errors", None)}')
        self.assertIn('step=2', response.url)

        response = self.client.post(apply + '?step=2', self.family_payload())
        self.assertEqual(response.status_code, 302)
        self.assertIn('step=3', response.url)

        response = self.client.post(apply + '?step=3', {
            'needs_bus': 'False',
            'has_other_child': 'False',
            'siblings-TOTAL_FORMS': '1',
            'siblings-INITIAL_FORMS': '0',
            'siblings-MIN_NUM_FORMS': '0',
            'siblings-MAX_NUM_FORMS': '1000',
            'siblings-0-name': '',
            'siblings-0-class_name': '',
        })
        if response.status_code != 302:
            ctx = response.context
            self.fail(
                f'step3 errors={ctx["form"].errors if ctx else None} '
                f'formset={ctx["sibling_formset"].errors if ctx else None}'
            )
        self.assertIn('step=4', response.url)

        response = self.client.post(apply + '?step=4', {
            'financial_capacity': 'True',
            'agrees_uniform': 'True',
            'agrees_rules': 'True',
            'info_correct': 'True',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('step=5', response.url)

        response = self.client.post(apply + '?step=5', {'slot_id': self.slot.pk})
        self.assertEqual(response.status_code, 302)
        self.assertIn('step=6', response.url)

        with patch('admissions.pdf.generate_and_store_pdf', side_effect=fake_store_pdf):
            with override_settings(
                EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                DEBUG=True,
            ):
                response = self.client.post(apply + '?step=6')
                self.assertEqual(response.status_code, 302)
                app = Application.objects.get(student_name_en='Rahim Ali')
                self.assertTrue(app.form_number)
                pay = reverse('admissions:simulate_payment', kwargs={'token': app.access_token})
                response = self.client.post(pay, {'outcome': 'success'})
                self.assertEqual(response.status_code, 302)
                app.refresh_from_db()
                self.assertTrue(app.is_paid)
                success = self.client.get(
                    reverse('admissions:success', kwargs={'token': app.access_token})
                )
                self.assertEqual(success.status_code, 200)
                pdf = self.client.get(
                    reverse('admissions:pdf_download', kwargs={'token': app.access_token})
                )
                self.assertEqual(pdf.status_code, 200)
                self.assertIn('Boalia', app.present_address)
                self.assertIn('Sagorpara', app.father_address)


class GeoAddressTests(AdmissionBaseTestCase):
    def test_compose_and_validate(self):
        from .geo import compose, is_valid, divisions
        self.assertIn('Rajshahi', divisions())
        self.assertTrue(is_valid('Rajshahi', 'Rajshahi', 'Boalia'))
        self.assertFalse(is_valid('Rajshahi', 'Rajshahi', 'Gulshan'))
        self.assertEqual(
            compose('Rajshahi', 'Rajshahi', 'Boalia', 'House 12'),
            'House 12, Boalia, Rajshahi, Rajshahi',
        )

    def test_invalid_thana_is_rejected(self):
        photo = make_photo_file()
        self.client.get(reverse('admissions:apply'))
        response = self.client.post(reverse('admissions:apply') + '?step=1', self.student_payload(
            birth_registration_no='19901234567890901',
            present_thana='Gulshan',
            photo=photo,
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'thana')

    def test_copy_present_to_permanent(self):
        photo = make_photo_file()
        self.client.get(reverse('admissions:apply'))
        response = self.client.post(reverse('admissions:apply') + '?step=1', self.student_payload(
            birth_registration_no='19901234567890902',
            photo=photo,
        ))
        self.assertEqual(response.status_code, 302)
        app = Application.objects.get(birth_registration_no='19901234567890902')
        self.assertEqual(app.permanent_thana, 'Boalia')
        self.assertEqual(app.permanent_division, 'Rajshahi')
        self.assertEqual(app.permanent_address, app.present_address)


class SiblingFormTests(AdmissionBaseTestCase):
    def test_multiple_siblings_saved(self):
        app = self.make_application(birth_registration_no='19901234567890903')
        app.wizard_step = 3
        app.save()
        self.client.cookies[RESUME_COOKIE] = str(app.resume_token)
        response = self.client.post(reverse('admissions:apply') + '?step=3', {
            'needs_bus': 'False',
            'has_other_child': 'True',
            'siblings-TOTAL_FORMS': '2',
            'siblings-INITIAL_FORMS': '0',
            'siblings-MIN_NUM_FORMS': '0',
            'siblings-MAX_NUM_FORMS': '12',
            'siblings-0-name': 'Amina Ali',
            'siblings-0-class_name': self.klass.name,
            'siblings-1-name': 'Hasan Ali',
            'siblings-1-class_name': self.klass.name,
        })
        if response.status_code != 302:
            ctx = response.context
            self.fail(
                f'status={response.status_code} errors={ctx["form"].errors if ctx else None} '
                f'formset={ctx["sibling_formset"].errors if ctx else None}'
            )
        app.refresh_from_db()
        names = list(app.siblings.values_list('name', 'class_name'))
        self.assertEqual(names, [('Amina Ali', 'Class 1'), ('Hasan Ali', 'Class 1')])


class PreviousResultTests(AdmissionBaseTestCase):
    def test_results_are_optional(self):
        app = self.make_application(birth_registration_no='19901234567890904')
        app.wizard_step = 2
        app.save()
        self.client.cookies[RESUME_COOKIE] = str(app.resume_token)
        response = self.client.post(reverse('admissions:apply') + '?step=2', self.family_payload(
            previous_school_name='Rajshahi Model School',
        ))
        if response.status_code != 302:
            ctx = response.context
            self.fail(
                f'status={response.status_code} errors={ctx["form"].errors if ctx else None} '
                f'formset={ctx["result_formset"].errors if ctx else None}'
            )
        app.refresh_from_db()
        self.assertEqual(app.previous_school_name, 'Rajshahi Model School')
        self.assertEqual(app.previous_results.count(), 0)


class PdfTemplateTests(AdmissionBaseTestCase):
    def test_paper_form_layout_includes_all_fields(self):
        from django.template.loader import render_to_string

        from admissions.models import PreviousResult, Sibling
        from admissions.pdf import build_pdf_context, render_pdf_bytes

        app = self.make_application(
            form_number='HCR-2026-00001',
            father_designation='Senior Teacher',
            father_organization='Rajshahi College',
            previous_school_name='Model School',
            has_other_child=True,
        )
        Sibling.objects.create(application=app, name='Amina Ali', class_name='Class 1')
        PreviousResult.objects.create(
            application=app, previous_class='KG', year='2024', result='A+',
        )
        html = render_to_string('admissions/pdf/application.html', build_pdf_context(app))
        self.assertIn('Application No', html)
        self.assertNotIn('Form Number:', html)
        self.assertIn('Admit Card', html)
        self.assertIn('Student Information', html)
        self.assertIn('Family Information', html)
        self.assertIn('Others Information', html)
        self.assertIn('Bus Information', html)
        self.assertIn('Declaration', html)
        self.assertIn('Viva Time', html)
        self.assertIn('Instructions', html)
        self.assertIn('Name of Student in English', html)
        self.assertIn('RAHIM ALI', html)
        self.assertIn('রহিম আলী', html)
        self.assertIn('Father’s Name in English', html)
        self.assertIn('Mother’s Name in English', html)
        self.assertIn('Present Address', html)
        self.assertIn('Permanent Address', html)
        self.assertIn('Father’s Work Address', html)
        self.assertIn('Mother’s Work Address', html)
        self.assertIn('Birth Registration No.', html)
        self.assertIn('Previous class', html)
        self.assertIn('Amina Ali', html)
        self.assertIn('Holy Cross School', html)
        self.assertIn('Hard-copy photograph', html)
        self.assertIn('Uploaded photo', html)
        self.assertIn('Student photograph', html)
        self.assertNotIn('BANDURA', html)
        pdf = render_pdf_bytes(app)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 2000)


class FormFixTests(AdmissionBaseTestCase):
    def test_second_apply_after_paid_starts_new_draft(self):
        app = self.make_application()
        app.status = Application.Status.PAID
        app.payment_status = Application.PaymentStatus.PAID
        app.save()
        self.client.cookies[RESUME_COOKIE] = str(app.resume_token)
        response = self.client.get(reverse('admissions:apply') + '?new=1')
        self.assertEqual(response.status_code, 200)
        new_app = Application.objects.exclude(pk=app.pk).get(session=self.session)
        self.assertEqual(new_app.status, Application.Status.DRAFT)
        self.assertNotEqual(str(new_app.resume_token), str(app.resume_token))

    def test_siblings_no_clears_partial_rows(self):
        app = self.make_application(birth_registration_no='19901234567890913')
        app.wizard_step = 3
        app.save()
        self.client.cookies[RESUME_COOKIE] = str(app.resume_token)
        response = self.client.post(reverse('admissions:apply') + '?step=3', {
            'needs_bus': 'False',
            'has_other_child': 'False',
            'siblings-TOTAL_FORMS': '1',
            'siblings-INITIAL_FORMS': '0',
            'siblings-MIN_NUM_FORMS': '0',
            'siblings-MAX_NUM_FORMS': '12',
            'siblings-0-name': 'Autofill Child',
            'siblings-0-class_name': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('step=4', response.url)
        app.refresh_from_db()
        self.assertFalse(app.has_other_child)
        self.assertEqual(app.siblings.count(), 0)

    def test_bengali_rejects_english(self):
        photo = make_photo_file()
        self.client.get(reverse('admissions:apply'))
        response = self.client.post(
            reverse('admissions:apply') + '?step=1',
            self.student_payload(student_name_bn='Rahim Ali', photo=photo),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Use Bengali characters only')

    def test_birth_registration_lengths(self):
        from admissions.utils import validate_birth_registration
        from django.core.exceptions import ValidationError

        self.assertEqual(validate_birth_registration('1234567890123'), '1234567890123')
        self.assertEqual(validate_birth_registration('1234567890123456'), '1234567890123456')
        self.assertEqual(validate_birth_registration('12345678901234567'), '12345678901234567')
        with self.assertRaises(ValidationError):
            validate_birth_registration('12345678901234')

    def test_unknown_blood_group_not_offered(self):
        from admissions.forms import StudentStepForm

        form = StudentStepForm()
        values = [value for value, _label in form.fields['blood_group'].choices]
        self.assertNotIn('Unknown', values)

    def test_bus_start_and_end_required_when_yes(self):
        app = self.make_application(birth_registration_no='19901234567890914')
        app.wizard_step = 3
        app.save()
        self.client.cookies[RESUME_COOKIE] = str(app.resume_token)
        response = self.client.post(reverse('admissions:apply') + '?step=3', {
            'needs_bus': 'True',
            'has_other_child': 'False',
            'siblings-TOTAL_FORMS': '1',
            'siblings-INITIAL_FORMS': '0',
            'siblings-MIN_NUM_FORMS': '0',
            'siblings-MAX_NUM_FORMS': '12',
            'siblings-0-name': '',
            'siblings-0-class_name': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'starting stop')
        response = self.client.post(reverse('admissions:apply') + '?step=3', {
            'needs_bus': 'True',
            'bus_start_stop': self.stop.pk,
            'bus_end_stop': self.stop.pk,
            'has_other_child': 'False',
            'siblings-TOTAL_FORMS': '1',
            'siblings-INITIAL_FORMS': '0',
            'siblings-MIN_NUM_FORMS': '0',
            'siblings-MAX_NUM_FORMS': '12',
            'siblings-0-name': '',
            'siblings-0-class_name': '',
        })
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertTrue(app.needs_bus)
        self.assertEqual(app.bus_start_stop_id, self.stop.pk)
        self.assertEqual(app.bus_end_stop_id, self.stop.pk)

    def test_nursery_skips_viva_step(self):
        nursery = AdmissionClass.objects.get(code='nursery')
        nursery.assigned_viva_date = date(2026, 2, 10)
        nursery.assigned_viva_start_time = time(9, 0)
        nursery.assigned_viva_end_time = time(10, 0)
        nursery.is_active = True
        nursery.save()
        photo = make_photo_file()
        apply = reverse('admissions:apply')
        self.client.get(apply)
        response = self.client.post(apply + '?step=1', self.student_payload(
            admit_class=nursery.pk,
            photo=photo,
            birth_registration_no='19901234567890921',
        ))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(apply + '?step=2', self.family_payload())
        self.assertEqual(response.status_code, 302)
        response = self.client.post(apply + '?step=3', {
            'needs_bus': 'False',
            'has_other_child': 'False',
            'siblings-TOTAL_FORMS': '1',
            'siblings-INITIAL_FORMS': '0',
            'siblings-MIN_NUM_FORMS': '0',
            'siblings-MAX_NUM_FORMS': '12',
            'siblings-0-name': '',
            'siblings-0-class_name': '',
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.post(apply + '?step=4', {
            'financial_capacity': 'True',
            'agrees_uniform': 'True',
            'agrees_rules': 'True',
            'info_correct': 'True',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('step=6', response.url)
        app = Application.objects.get(birth_registration_no='19901234567890921')
        self.assertTrue(app.skips_viva_selection)
        self.assertEqual(app.display_viva_date, date(2026, 2, 10))
        self.assertTrue(app.ready_for_payment)

    def test_class_7_requires_class_6_reg(self):
        klass = AdmissionClass.objects.get(code='class-7')
        klass.is_active = True
        klass.save()
        photo = make_photo_file()
        self.client.get(reverse('admissions:apply'))
        response = self.client.post(
            reverse('admissions:apply') + '?step=1',
            self.student_payload(admit_class=klass.pk, photo=photo, birth_registration_no='19901234567890922'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Class 6 registration')
        response = self.client.post(
            reverse('admissions:apply') + '?step=1',
            self.student_payload(
                admit_class=klass.pk,
                photo=make_photo_file(),
                birth_registration_no='19901234567890922',
                class_6_reg_no='REG6001',
            ),
        )
        self.assertEqual(response.status_code, 302)

    def test_class_9_requires_regs_and_group(self):
        klass = AdmissionClass.objects.get(code='class-9')
        klass.is_active = True
        klass.save()
        photo = make_photo_file()
        self.client.get(reverse('admissions:apply'))
        response = self.client.post(
            reverse('admissions:apply') + '?step=1',
            self.student_payload(
                admit_class=klass.pk,
                photo=photo,
                birth_registration_no='19901234567890923',
                class_6_reg_no='REG6001',
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Class 8 registration')
        response = self.client.post(
            reverse('admissions:apply') + '?step=1',
            self.student_payload(
                admit_class=klass.pk,
                photo=make_photo_file(),
                birth_registration_no='19901234567890923',
                class_6_reg_no='REG6001',
                class_8_reg_no='REG8001',
                study_group=Application.StudyGroup.SCIENCE,
            ),
        )
        self.assertEqual(response.status_code, 302)
        app = Application.objects.get(birth_registration_no='19901234567890923')
        self.assertEqual(app.study_group, Application.StudyGroup.SCIENCE)

    def test_landing_shows_application_terms(self):
        response = self.client.get(reverse('admissions:landing'))
        self.assertContains(response, 'আবেদনের শর্তাবলি')
        self.assertNotContains(response, 'How it works')

    def test_sibling_class_dropdown_includes_inactive(self):
        from admissions.forms import admission_class_choices

        AdmissionClass.objects.filter(code='class-xii').update(is_active=False)
        names = [label for _value, label in admission_class_choices() if _value]
        self.assertIn('Class XII', names)
        self.assertIn('Play', names)

    def test_guardian_father_copies_parent_name(self):
        app = self.make_application(birth_registration_no='19901234567890931')
        app.wizard_step = 2
        app.save()
        self.client.cookies[RESUME_COOKIE] = str(app.resume_token)
        response = self.client.post(
            reverse('admissions:apply') + '?step=2',
            self.family_payload(guardian_type=Application.GuardianType.FATHER),
        )
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.guardian_type, Application.GuardianType.FATHER)
        self.assertEqual(app.guardian_name, 'Karim Ali')
        self.assertEqual(app.guardian_relation, 'Father')
        self.assertEqual(app.guardian_phone, '01711111111')

    def test_guardian_other_requires_name_and_relation(self):
        app = self.make_application(birth_registration_no='19901234567890932')
        app.wizard_step = 2
        app.save()
        self.client.cookies[RESUME_COOKIE] = str(app.resume_token)
        response = self.client.post(
            reverse('admissions:apply') + '?step=2',
            self.family_payload(
                guardian_type=Application.GuardianType.OTHER,
                guardian_name='',
                guardian_relation='',
                guardian_phone='',
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'guardian')
        response = self.client.post(
            reverse('admissions:apply') + '?step=2',
            self.family_payload(
                guardian_type=Application.GuardianType.OTHER,
                guardian_name='Abdul Karim',
                guardian_relation='Uncle',
                guardian_phone='01612345678',
            ),
        )
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.guardian_name, 'Abdul Karim')
        self.assertEqual(app.guardian_relation, 'Uncle')
        self.assertEqual(app.guardian_phone, '01612345678')





