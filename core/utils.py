import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile


def convert_image_to_webp(image_field, quality=90, force=False):
    """
    Converts an ImageField's image to WebP format if it is not already in WebP format.
    Updates the field with the new WebP file without altering the original framing.
    """
    if not image_field or not hasattr(image_field, 'name') or not image_field.name:
        return False

    filename = os.path.basename(image_field.name)
    if not filename:
        return False

    name_without_ext, ext = os.path.splitext(filename)
    if ext.lower() == '.webp' and not force:
        return False

    try:
        image_field.open()
        img = Image.open(image_field)

        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=quality, optimize=True)
        buffer.seek(0)

        new_filename = f"{name_without_ext}.webp" if ext.lower() != '.webp' else filename
        image_field.save(new_filename, ContentFile(buffer.read()), save=False)
        return True
    except Exception as e:
        print(f"Error converting image {image_field.name} to WebP: {e}")
        return False
