import os
from io import BytesIO
from PIL import Image, ImageFilter, ImageStat
from django.core.files.base import ContentFile


def process_image_to_pro_headshot(image_field, target_width=600, target_height=800, quality=92, force=False):
    """
    Enterprise-Grade Pro Headshot Auto-Framing Algorithm:
    1. Detects and strips away artificial blurred/padding borders if present.
    2. Dynamically crops the subject into a crisp, perfectly framed 3:4 portrait headshot:
       - For wide landscape photos: crops side backgrounds and zooms into the teacher's face & upper body.
       - For tall portrait photos: anchors crop near top so head & face are perfectly positioned.
    3. Resizes to 600x800 high-quality WebP format.
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

        w, h = img.size
        gray = img.convert('L')
        edges = gray.filter(ImageFilter.FIND_EDGES)

        # Detect sharp inner bounds if image has artificial padded/blurred borders
        row_stats = [ImageStat.Stat(edges.crop((0, y, w, y + 1))).mean[0] for y in range(h)]
        col_stats = [ImageStat.Stat(edges.crop((x, 0, x + 1, h))).mean[0] for x in range(w)]

        y1 = 0
        for y in range(10, h - 10):
            if row_stats[y] >= 1.0 and row_stats[y+1] >= 1.0 and row_stats[y+2] >= 1.0:
                y1 = y
                break

        y2 = h
        for y in range(h - 11, 10, -1):
            if row_stats[y] >= 1.0 and row_stats[y-1] >= 1.0 and row_stats[y-2] >= 1.0:
                y2 = y
                break

        x1 = 0
        for x in range(10, w - 10):
            if col_stats[x] >= 1.0 and col_stats[x+1] >= 1.0 and col_stats[x+2] >= 1.0:
                x1 = x
                break

        x2 = w
        for x in range(w - 11, 10, -1):
            if col_stats[x] >= 1.0 and col_stats[x-1] >= 1.0 and col_stats[x-2] >= 1.0:
                x2 = x
                break

        if (y2 - y1) < h * 0.3:
            y1, y2 = 0, h
        if (x2 - x1) < w * 0.3:
            x1, x2 = 0, w

        clean_img = img.crop((x1, y1, x2, y2))
        pw, ph = clean_img.size
        aspect = pw / ph
        target_aspect = target_width / target_height  # 0.75

        if 0.72 <= aspect <= 0.78:
            cropped = clean_img
        elif aspect > target_aspect:
            # Landscape photo: Crop side backgrounds, zoom in on subject center
            crop_w = int(ph * target_aspect)
            offset_x = (pw - crop_w) // 2
            cropped = clean_img.crop((offset_x, 0, offset_x + crop_w, ph))
        else:
            # Tall photo: Anchor crop near top (head/face focus)
            crop_h = int(pw / target_aspect)
            offset_y = int((ph - crop_h) * 0.15)
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
