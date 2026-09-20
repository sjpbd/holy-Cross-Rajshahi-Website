from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0009_guardian_is'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='guardian_phone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Guardian phone'),
        ),
    ]
