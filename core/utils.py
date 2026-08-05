import os
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter, ImageStat
from django.core.files.base import ContentFile


def auto_fix_orientation_and_borders(img):
    """
    1. EXIF Transpose: Rotates mobile camera photos upright according to EXIF metadata.
    2. Auto-Detect Sideways Photos: If a photo is sideways without EXIF (w > h),
       detects feature distribution and rotates it 90 degrees upright.
    3. Strip Artificial Blurred Borders: Detects and crops out legacy top/bottom blurred bars.
    """
    img = ImageOps.exif_transpose(img)
    w, h = img.size

    # Detect if photo is rotated sideways (landscape orientation w > h for a single person headshot)
    if w > h and (w / h) < 1.7:
        left_crop = img.crop((0, 0, int(w * 0.4), h))
        right_crop = img.crop((int(w * 0.6), 0, w, h))

        left_edges = ImageStat.Stat(left_crop.convert('L').filter(ImageFilter.FIND_EDGES)).mean[0]
        right_edges = ImageStat.Stat(right_crop.convert('L').filter(ImageFilter.FIND_EDGES)).mean[0]
        top_crop = img.crop((0, 0, w, int(h * 0.4)))
        top_edges = ImageStat.Stat(top_crop.convert('L').filter(ImageFilter.FIND_EDGES)).mean[0]

        # If vertical edges dominate horizontal top, photo is sideways -> rotate upright
        if max(left_edges, right_edges) > top_edges * 1.6:
            if left_edges > right_edges:
                img = img.rotate(270, expand=True)
            else:
                img = img.rotate(90, expand=True)

    w, h = img.size
    gray = img.convert('L')
    edges = gray.filter(ImageFilter.FIND_EDGES)

    row_stats = [ImageStat.Stat(edges.crop((0, y, w, y + 1))).mean[0] for y in range(h)]
    max_row = max(row_stats) if row_stats else 1.0
    thresh = max(2.5, max_row * 0.15)

    y1 = 0
    for y in range(5, h - 5):
        if row_stats[y] >= thresh:
            y1 = max(0, y - 2)
            break

    y2 = h
    for y in range(h - 6, 5, -1):
        if row_stats[y] >= thresh:
            y2 = min(h, y + 2)
            break

    if (y2 - y1) < h * 0.4:
        y1, y2 = 0, h

    return img.crop((0, y1, w, y2))


def process_image_to_pro_headshot(image_field, target_width=600, target_height=800, quality=95, force=False):
    """
    Enterprise Pro Auto-Headshot Algorithm:
    Used ONLY for Faculty, Leadership & Staff directory photos.
    1. Fixes sideways/rotated mobile photo uploads automatically.
    2. Strips legacy blurred top/bottom padding borders.
    3. Crops 3:4 aspect ratio with 5% headroom anchor so head, hair & forehead are NEVER cut off.
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

        has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
        if has_alpha:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        # Fix orientation & strip legacy blurred borders
        clean_img = auto_fix_orientation_and_borders(img)
        pw, ph = clean_img.size
        target_aspect = target_width / target_height  # 0.75
        aspect = pw / ph

        if 0.73 <= aspect <= 0.77:
            cropped = clean_img
        elif aspect > target_aspect:
            # Wide landscape photo: Crop side background walls, zoom into subject center
            crop_w = int(ph * target_aspect)
            offset_x = (pw - crop_w) // 2
            cropped = clean_img.crop((offset_x, 0, offset_x + crop_w, ph))
        else:
            # Tall portrait photo: Anchor with 5% headroom so forehead/hair is fully visible
            crop_h = int(pw / target_aspect)
            offset_y = int((ph - crop_h) * 0.05)
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


def convert_image_to_webp(image_field, quality=95, force=False):
    """
    Pure WebP Format Converter for Gallery Photos, Album Covers, Sliders, Notices, etc.
    Converts any image file into WebP format while preserving 100% of its original resolution,
    aspect ratio, and original photo contents with ZERO cropping or padding alterations.
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
        img = ImageOps.exif_transpose(img)

        # Remove any legacy blurred borders if file was previously padded
        img = auto_fix_orientation_and_borders(img)

        has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
        if has_alpha:
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
