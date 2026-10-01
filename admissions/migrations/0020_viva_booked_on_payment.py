from django.db import migrations
from django.db.models import Count, Q


def recount_paid_bookings(apps, schema_editor):
    VivaSlot = apps.get_model('admissions', 'VivaSlot')
    slots = VivaSlot.objects.annotate(
        paid=Count('applications', filter=Q(applications__paid_at__isnull=False)),
    )
    for slot in slots:
        if slot.booked_count != slot.paid:
            VivaSlot.objects.filter(pk=slot.pk).update(booked_count=slot.paid)


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0019_previousresult_exam'),
    ]

    operations = [
        migrations.RunPython(recount_paid_bookings, migrations.RunPython.noop),
    ]
