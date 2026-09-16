from django.db import migrations, models


FORM_CODES = {
    'play': 'P',
    'nursery': 'N',
    'kg': 'KG',
    'class-1': '1',
    'class-2': '2',
    'class-3': '3',
    'class-4': '4',
    'class-5': '5',
    'class-6': '6',
    'class-7': '7',
    'class-8': '8',
    'class-9': '9',
    'class-10': '10',
    'class-xi': 'XI',
    'class-xii': 'XII',
}


def seed_form_codes(apps, schema_editor):
    AdmissionClass = apps.get_model('admissions', 'AdmissionClass')
    for klass in AdmissionClass.objects.all():
        if klass.form_code:
            continue
        code = FORM_CODES.get((klass.code or '').lower())
        if not code and (klass.name or '').lower().startswith('class '):
            code = klass.name.split(None, 1)[1].replace(' ', '').upper()
        if code:
            klass.form_code = code
            klass.save(update_fields=['form_code'])


class Migration(migrations.Migration):
    dependencies = [
        ('admissions', '0005_previous_result_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='admissionclass',
            name='form_code',
            field=models.CharField(
                blank=True,
                help_text='Prefix on form numbers, e.g. N for Nursery → N-26-00001.',
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name='application',
            name='permanent_address',
            field=models.TextField(blank=True, help_text='Composed full permanent address'),
        ),
        migrations.AddField(
            model_name='application',
            name='permanent_address_line',
            field=models.CharField(
                blank=True,
                help_text='House, road, village or area',
                max_length=300,
                verbose_name='Permanent address',
            ),
        ),
        migrations.AddField(
            model_name='application',
            name='permanent_division',
            field=models.CharField(blank=True, max_length=80, verbose_name='Permanent division'),
        ),
        migrations.AddField(
            model_name='application',
            name='permanent_thana',
            field=models.CharField(blank=True, max_length=80, verbose_name='Permanent thana'),
        ),
        migrations.AddField(
            model_name='application',
            name='permanent_zila',
            field=models.CharField(blank=True, max_length=80, verbose_name='Permanent zila'),
        ),
        migrations.AlterField(
            model_name='application',
            name='father_address',
            field=models.TextField(blank=True, help_text='Composed full father work address'),
        ),
        migrations.AlterField(
            model_name='application',
            name='father_address_line',
            field=models.CharField(blank=True, max_length=300, verbose_name="Father's work address"),
        ),
        migrations.AlterField(
            model_name='application',
            name='mother_address',
            field=models.TextField(blank=True, help_text='Composed full mother work address'),
        ),
        migrations.AlterField(
            model_name='application',
            name='mother_address_line',
            field=models.CharField(blank=True, max_length=300, verbose_name="Mother's work address"),
        ),
        migrations.AddField(
            model_name='admissionsequence',
            name='class_code',
            field=models.CharField(default='', max_length=8),
        ),
        migrations.AlterField(
            model_name='admissionsequence',
            name='year',
            field=models.CharField(max_length=4),
        ),
        migrations.AlterUniqueTogether(
            name='admissionsequence',
            unique_together={('year', 'class_code')},
        ),
        migrations.RunPython(seed_form_codes, migrations.RunPython.noop),
    ]
