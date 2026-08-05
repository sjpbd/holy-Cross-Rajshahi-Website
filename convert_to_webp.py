import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'holy_cross.settings')
django.setup()

from django.conf import settings
from people.models import Teacher, Administration, Staff, GoverningBodyMember
from core.models import SchoolInfo
from gallery.models import Album, Photo
from core.utils import convert_image_to_webp

def process_model_images(model_cls, image_field_name):
    count = 0
    for obj in model_cls.objects.all():
        image_field = getattr(obj, image_field_name)
        if image_field and image_field.name:
            if convert_image_to_webp(image_field):
                obj.save(update_fields=[image_field_name])
                print(f"Converted {model_cls.__name__} (ID: {obj.pk}) {image_field_name} -> {image_field.name}")
                count += 1
            else:
                print(f"Skipped {model_cls.__name__} (ID: {obj.pk}) {image_field_name} ({image_field.name})")
    return count

def clean_cached_thumbnails():
    media_root = settings.MEDIA_ROOT
    removed = 0
    for root, dirs, files in os.walk(media_root):
        for f in files:
            if '_crop-' in f or '.400x500_' in f or '.300x400_' in f or '.200x200_' in f or '.500x500_' in f or '.150x150_' in f:
                path = os.path.join(root, f)
                try:
                    os.remove(path)
                    removed += 1
                except Exception as e:
                    print(f"Could not remove {path}: {e}")
    print(f"Removed {removed} old thumbnail cache files.")

def main():
    print("Starting WebP conversion for people, administration, and gallery images...")
    t_count = process_model_images(Teacher, 'photo')
    a_count = process_model_images(Administration, 'photo')
    s_count = process_model_images(Staff, 'photo')
    g_count = process_model_images(GoverningBodyMember, 'photo')

    album_count = process_model_images(Album, 'cover_image')
    photo_count = process_model_images(Photo, 'image')

    # SchoolInfo principal & vice principal
    info = SchoolInfo.load()
    info_updated = False
    if info.principal_photo and convert_image_to_webp(info.principal_photo):
        info_updated = True
        print(f"Converted SchoolInfo principal_photo -> {info.principal_photo.name}")
    if info.vice_principal_photo and convert_image_to_webp(info.vice_principal_photo):
        info_updated = True
        print(f"Converted SchoolInfo vice_principal_photo -> {info.vice_principal_photo.name}")
    if info_updated:
        info.save()

    clean_cached_thumbnails()
    print("WebP conversion completed successfully!")

if __name__ == '__main__':
    main()
