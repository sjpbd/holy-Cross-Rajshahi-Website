# admissions/excel.py
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font


def sanitize_excel(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    if text[:1] in {'=', '+', '-', '@'}:
        return f"'{text}"
    return text


def applications_workbook(queryset):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Applications'
    headers = [
        'Application No', 'Status', 'Payment', 'Class', 'Student (EN)', 'Student (BN)',
        'DOB', 'Age years', 'Age months', 'Birth registration', 'Nationality',
        'Blood group', 'Gender', 'Religion', 'Hobby', 'Other skills',
        'Class 6 registration', 'Class 8 registration', 'Group',
        'Present division', 'Present zila', 'Present thana', 'Present address line', 'Present address',
        'Permanent division', 'Permanent zila', 'Permanent thana', 'Permanent address line', 'Permanent address',
        'Father name', 'Father name (BN)', 'Father NID', 'Father occupation', 'Father designation',
        'Father organization', 'Father mobile',
        'Father division', 'Father zila', 'Father thana', 'Father work address line', 'Father work address',
        'Mother name', 'Mother name (BN)', 'Mother NID', 'Mother occupation', 'Mother designation',
        'Mother organization', 'Mother mobile',
        'Mother division', 'Mother zila', 'Mother thana', 'Mother work address line', 'Mother work address',
        'WhatsApp', 'Guardian is', 'Guardian name', 'Guardian relation', 'Guardian phone',
        'Email', 'Family income', 'Earning members', 'Previous school',
        'Previous results', 'Needs bus', 'Bus start', 'Bus end', 'Siblings',
        'Financial capacity', 'Agrees uniform', 'Agrees rules', 'Info correct',
        'Viva date', 'Viva time', 'Submitted at', 'Paid at', 'Email sent at',
        'Email error',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    qs = queryset.select_related(
        'admit_class', 'session', 'bus_start_stop', 'bus_end_stop', 'viva_slot',
    ).prefetch_related(
        'previous_results', 'siblings',
    )
    for app in qs:
        results = '; '.join(
            f'{r.previous_class} {r.year} {r.result}'.strip()
            for r in app.previous_results.all()
        )
        siblings = '; '.join(
            f'{s.name} ({s.class_name})'.strip()
            for s in app.siblings.all()
        )
        viva_date, viva_start, viva_end = app.viva_when()
        viva_date_text = viva_date.isoformat() if viva_date else ''
        viva_time = ''
        if viva_start:
            viva_time = viva_start.strftime('%H:%M')
            if viva_end:
                viva_time = f'{viva_time}–{viva_end.strftime("%H:%M")}'
        row = [
            app.form_number, app.get_status_display(), app.get_payment_status_display(),
            app.admit_class.name if app.admit_class_id else '',
            app.student_name_en, app.student_name_bn,
            app.date_of_birth.isoformat() if app.date_of_birth else '',
            app.age_years, app.age_months, app.birth_registration_no, app.nationality,
            app.blood_group, app.get_gender_display() if app.gender else '',
            app.get_religion_display() if app.religion else '',
            app.hobby, app.other_skills, app.class_6_reg_no, app.class_8_reg_no,
            app.get_study_group_display() if app.study_group else '',
            app.present_division, app.present_zila, app.present_thana, app.present_address_line,
            app.present_address,
            app.permanent_division, app.permanent_zila, app.permanent_thana, app.permanent_address_line,
            app.permanent_address,
            app.father_name, app.father_name_bn, app.father_nid, app.father_occupation, app.father_designation,
            app.father_organization, app.father_mobile,
            app.father_division, app.father_zila, app.father_thana, app.father_address_line,
            app.father_address,
            app.mother_name, app.mother_name_bn, app.mother_nid, app.mother_occupation, app.mother_designation,
            app.mother_organization, app.mother_mobile,
            app.mother_division, app.mother_zila, app.mother_thana, app.mother_address_line,
            app.mother_address,
            app.whatsapp_number, app.get_guardian_type_display() if app.guardian_type else '',
            app.guardian_name, app.guardian_relation, app.guardian_phone,
            app.email,
            app.get_family_income_yearly_display() if app.family_income_yearly else '',
            app.earning_members, app.previous_school_name,
            results, app.needs_bus,
            app.bus_start_stop.name if app.bus_start_stop_id else '',
            app.bus_end_stop.name if app.bus_end_stop_id else '',
            siblings, app.financial_capacity, app.agrees_uniform, app.agrees_rules, app.info_correct,
            viva_date_text, viva_time,
            app.submitted_at.isoformat() if app.submitted_at else '',
            app.paid_at.isoformat() if app.paid_at else '',
            app.confirmation_email_sent_at.isoformat() if app.confirmation_email_sent_at else '',
            app.confirmation_email_error,
        ]
        ws.append([sanitize_excel(v) for v in row])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
