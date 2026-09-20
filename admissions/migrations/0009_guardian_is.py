from django.db import migrations, models


def remap_guardian_type(apps, schema_editor):
    Application = apps.get_model('admissions', 'Application')
    Application.objects.filter(guardian_type__in=['primary', 'legal']).update(guardian_type='other')


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0008_form_fixes'),
    ]

    operations = [
        migrations.RunPython(remap_guardian_type, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='application',
            name='guardian_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('father', 'Father'),
                    ('mother', 'Mother'),
                    ('other', 'Other person'),
                ],
                max_length=16,
                verbose_name='Guardian is',
            ),
        ),
    ]
