from django.db import migrations


CLASSES = [
    ('Play', 'play', 0),
    ('Nursery', 'nursery', 1),
    ('KG', 'kg', 2),
    ('Class 1', 'class-1', 3),
    ('Class 2', 'class-2', 4),
    ('Class 3', 'class-3', 5),
    ('Class 4', 'class-4', 6),
    ('Class 5', 'class-5', 7),
    ('Class 6', 'class-6', 8),
    ('Class 7', 'class-7', 9),
    ('Class 8', 'class-8', 10),
    ('Class 9', 'class-9', 11),
    ('Class 10', 'class-10', 12),
    ('Class XI', 'class-xi', 13),
    ('Class XII', 'class-xii', 14),
]

STOPS = [
    'Court Station',
    'Shaheb Bazar',
    'New Market',
    'Laxmipur',
    'Railgate',
    'Padma Residential',
    'Kashiadanga',
]


def seed(apps, schema_editor):
    AdmissionClass = apps.get_model('admissions', 'AdmissionClass')
    BusStop = apps.get_model('admissions', 'BusStop')
    for name, code, order in CLASSES:
        AdmissionClass.objects.get_or_create(
            code=code,
            defaults={'name': name, 'order': order, 'is_active': True},
        )
    for index, name in enumerate(STOPS):
        BusStop.objects.get_or_create(name=name, defaults={'order': index, 'is_active': True})


def unseed(apps, schema_editor):
    AdmissionClass = apps.get_model('admissions', 'AdmissionClass')
    BusStop = apps.get_model('admissions', 'BusStop')
    AdmissionClass.objects.filter(code__in=[c[1] for c in CLASSES]).delete()
    BusStop.objects.filter(name__in=STOPS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('admissions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
