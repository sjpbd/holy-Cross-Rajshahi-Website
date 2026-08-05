import os
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter, ImageStat
from django.core.files.base import ContentFile


def strip_blurred_borders(img):
    """Detects and strips away artificial blurred/padded borders from previous generations."""
    w, h = img.size
    gray = img.convert('L')
    edges = gray.filter(ImageFilter.FIND_EDGES)

    row_stats = [ImageStat.Stat(edges.crop((0, y, w, y + 1))).mean[0] for y in range(h)]
    col_stats = [ImageStat.Stat(edges.crop((x, 0, x + 1, h))).mean[0] for x in range(w)]

    y1 = 0
    for y in range(10, h - 10):
        if row_stats[y] >= 1.0 and row_stats[y + 1] >= 1.0 and row_stats[y + 2] >= 1.0:
            y1 = y
            break

    y2 = h
    for y in range(h - 11, 10, -1):
        if row_stats[y] >= 1.0 and row_stats[y - 1] >= 1.0 and row_stats[y - 2] >= 1.0:
            y2 = y
            break

    x1 = 0
    for x in range(10, w - 10):
        if col_stats[x] >= 1.0 and col_stats[x + 1] >= 1.0 and col_stats[x + 2] >= 1.0:
            x1 = x
            break

    x2 = w
    for x in range(w - 11, 10, -1):
        if col_stats[x] >= 1.0 and col_stats[x - 1] >= 1.0 and col_stats[x - 2] >= 1.0:
            x2 = x
            break

    if (y2 - y1) < h * 0.3:
        y1, y2 = 0, h
    if (x2 - x1) < w * 0.3:
        x1, x2 = 0, w

    return img.crop((x1, y1, x2, y2))


def process_image_to_pro_headshot(image_field, target_width=600, target_height=800, quality=92, force=False):
    """
    Enterprise Pro Auto-Headshot Algorithm:
    1. ImageOps.exif_transpose: Fixes phone/camera EXIF rotation so photos are never sideways.
    2. strip_blurred_borders: Removes legacy artificial blurred/padded borders.
    3. Headroom-Anchored 3:4 Framing:
       - For landscape: crops side background walls and zooms into subject center.
       - For tall portrait: anchors crop with ~8% headroom so heads and hair are NEVER cut off.
    4. Resizes to high-quality 600x800 WebP format.
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

        # 1. EXIF Auto-Transpose (Fixes sideways / rotated mobile uploads)
        img = ImageOps.exif_transpose(img)

        has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
        if has_alpha:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        # 2. Strip artificial blurred borders if present
        clean_img = strip_blurred_borders(img)
        pw, ph = clean_img.size
        target_aspect = target_width / target_height  # 0.75
        aspect = pw / ph

        # 3. Smart Framing
        if 0.73 <= aspect <= 0.77:
            cropped = clean_img
        elif aspect > target_aspect:
            # Wide landscape photo: Crop side walls, zoom in on subject center
            crop_w = int(ph * target_aspect)
            offset_x = (pw - crop_w) // 2
            cropped = clean_img.crop((offset_x, 0, offset_x + crop_w, ph))
        else:
            # Tall portrait photo: Anchor with 8% headroom so forehead/hair is fully visible
            crop_h = int(pw / target_aspect)
            offset_y = int((ph - crop_h) * 0.08)
            offset_y = max(0, min(offset_y, ph - crop_h))
            cropped = clean_img.crop((0, offset_y, pw, offset_y + crop_h))

        final_img = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

        if final_img.mode != 'RGB' and not has_alpha:
            final_img = final_img.convert('RGB')

        buffer = BytesIO()
        final_img.save(buffer, format='WEBP', quality=quality, optimize=True)
        buffer.seek(0)

        new_filename = f"{name_without_ext}.webp" if ext.lower() != '.webp' else filename
        image_field.save(new_filename, ContentFile(buffer.read()), save=False)
        return True
    except Exception as e:
        print(f"Error processing pro headshot webp image {image_field.name}: {e}")
        return False


def convert_image_to_webp(image_field, quality=92, force=False):
    return process_image_to_pro_headshot(image_field, quality=quality, force=force)
