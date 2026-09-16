from django.db import migrations, models


INCOME_CHOICES = [
    ('below-6000', 'Below 6,000'),
    ('6000-10000', '6,000 – 10,000'),
    ('10000-15000', '10,000 – 15,000'),
    ('15000-20000', '15,000 – 20,000'),
    ('20000-25000', '20,000 – 25,000'),
    ('25000-30000', '25,000 – 30,000'),
    ('30000-40000', '30,000 – 40,000'),
    ('40000-50000', '40,000 – 50,000'),
    ('50000-75000', '50,000 – 75,000'),
    ('75000-100000', '75,000 – 100,000'),
    ('100000-150000', '100,000 – 150,000'),
    ('150000-200000', '150,000 – 200,000'),
    ('above-200000', 'Above 200,000'),
]

VALID_CODES = {code for code, _label in INCOME_CHOICES}

# Inclusive upper bounds, lowest first. 10,000 stays in 6,000–10,000.
RANGE_UPPER = [
    (5999, 'below-6000'),
    (10000, '6000-10000'),
    (15000, '10000-15000'),
    (20000, '15000-20000'),
    (25000, '20000-25000'),
    (30000, '25000-30000'),
    (40000, '30000-40000'),
    (50000, '40000-50000'),
    (75000, '50000-75000'),
    (100000, '75000-100000'),
    (150000, '100000-150000'),
    (200000, '150000-200000'),
]


def map_income(value):
    if value in (None, ''):
        return ''
    text = str(value).strip()
    if text in VALID_CODES:
        return text
    digits = text.replace(',', '').replace(' ', '')
    try:
        amount = int(float(digits))
    except (TypeError, ValueError):
        return ''
    for upper, code in RANGE_UPPER:
        if amount <= upper:
            return code
    return 'above-200000'


def convert_family_income(apps, schema_editor):
    Application = apps.get_model('admissions', 'Application')
    for app in Application.objects.all().only('id', 'family_income_yearly'):
        mapped = map_income(app.family_income_yearly)
        if mapped != (app.family_income_yearly or ''):
            app.family_income_yearly = mapped
            app.save(update_fields=['family_income_yearly'])


class Migration(migrations.Migration):
    dependencies = [
        ('admissions', '0006_permanent_address_and_form_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='family_income_yearly',
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                verbose_name='Family income (yearly, BDT)',
            ),
        ),
        migrations.RunPython(convert_family_income, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='application',
            name='family_income_yearly',
            field=models.CharField(
                blank=True,
                choices=INCOME_CHOICES,
                max_length=32,
                verbose_name='Family income (yearly, BDT)',
            ),
        ),
    ]
