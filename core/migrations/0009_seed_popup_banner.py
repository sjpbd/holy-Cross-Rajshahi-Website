from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations

POSTER = Path(settings.BASE_DIR) / 'static' / 'images' / 'admission-2027-poster.jpg'


def seed_popup(apps, schema_editor):
    PopupBanner = apps.get_model('core', 'PopupBanner')
    if PopupBanner.objects.exists() or not POSTER.exists():
        return
    name = f'popup/{POSTER.name}'
    if not default_storage.exists(name):
        with POSTER.open('rb') as fh:
            name = default_storage.save(name, File(fh))
    PopupBanner.objects.create(
        title='Holy Cross School & College Admission 2027 - Online application begins 1 October 2026',
        image=name,
        link='/admission/',
        button_text='Apply Now',
        is_active=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_popupbanner'),
    ]

    operations = [
        migrations.RunPython(seed_popup, migrations.RunPython.noop),
    ]
