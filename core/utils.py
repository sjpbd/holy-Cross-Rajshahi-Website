import os
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance
from django.core.files.base import ContentFile


def process_image_to_studio_webp(image_field, target_width=600, target_height=800, quality=90, force=False):
    """
    Standardizes an uploaded image into a professional 3:4 WebP portrait canvas (600x800).
    - If the image is non-standard aspect ratio (like landscape), it fills the background with
      a soft blurred ambient background of the photo and pastes the uncropped original in the center.
    - Saves the image in WebP format.
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

        has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
        if has_alpha:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        orig_w, orig_h = img.size
        orig_aspect = orig_w / orig_h

        # Target aspect 3:4 = 0.75
        if 0.72 <= orig_aspect <= 0.78:
            final_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        else:
            # Aspect fill for background
            scale_bg = max(target_width / orig_w, target_height / orig_h)
            bg_w, bg_h = int(orig_w * scale_bg), int(orig_h * scale_bg)
            bg_resized = img.resize((bg_w, bg_h), Image.Resampling.LANCZOS)

            # Center crop background
            left = (bg_w - target_width) // 2
            top = (bg_h - target_height) // 2
            bg_cropped = bg_resized.crop((left, top, left + target_width, top + target_height))

            # Apply soft studio Gaussian blur & gentle darkening
            bg_blurred = bg_cropped.filter(ImageFilter.GaussianBlur(radius=28))
            if bg_blurred.mode == 'RGBA':
                overlay = Image.new('RGBA', (target_width, target_height), (15, 23, 42, 110))
                bg_blurred = Image.alpha_composite(bg_blurred, overlay).convert('RGB')
            else:
                enhancer = ImageEnhance.Brightness(bg_blurred)
                bg_blurred = enhancer.enhance(0.78)

            # Aspect fit foreground
            scale_fg = min(target_width / orig_w, target_height / orig_h)
            fg_w, fg_h = int(orig_w * scale_fg), int(orig_h * scale_fg)
            fg_resized = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

            paste_x = (target_width - fg_w) // 2
            paste_y = (target_height - fg_h) // 2

            final_img = bg_blurred.copy()
            if has_alpha and fg_resized.mode == 'RGBA':
                final_img.paste(fg_resized, (paste_x, paste_y), fg_resized)
            else:
                final_img.paste(fg_resized, (paste_x, paste_y))

        if final_img.mode != 'RGB' and not has_alpha:
            final_img = final_img.convert('RGB')

        buffer = BytesIO()
        final_img.save(buffer, format='WEBP', quality=quality, optimize=True)
        buffer.seek(0)

        new_filename = f"{name_without_ext}.webp" if ext.lower() != '.webp' else filename
        image_field.save(new_filename, ContentFile(buffer.read()), save=False)
        return True
    except Exception as e:
        print(f"Error processing studio webp image {image_field.name}: {e}")
        return False


def convert_image_to_webp(image_field, quality=90, force=False):
    return process_image_to_studio_webp(image_field, quality=quality, force=force)
