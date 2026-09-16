# admissions/utils.py
from io import BytesIO
from pathlib import Path

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .constants import CACHE_SKIP_PREFIXES

MIN_PHOTO_BYTES = 50 * 1024
MAX_PHOTO_BYTES = 2 * 1024 * 1024
MIN_PHOTO_DIM = 300
MAX_PHOTO_WIDTH = 600
MAX_PHOTO_HEIGHT = 800
ALLOWED_PHOTO_TYPES = {'JPEG', 'PNG'}
ALLOWED_PHOTO_EXTS = {'.jpg', '.jpeg', '.png'}


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def should_skip_cache(request):
    path = request.path or ''
    return any(path.startswith(prefix) for prefix in CACHE_SKIP_PREFIXES)


def lookup_rate_limited(request, action, limit=8, window=600):
    ip = client_ip(request) or 'unknown'
    key = f'admission-rate:{action}:{ip}'
    count = cache.get(key, 0) + 1
    cache.set(key, count, window)
    return count > limit


def validate_bd_mobile(value):
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    if len(digits) == 13 and digits.startswith('880'):
        digits = digits[3:]
    if len(digits) == 11 and digits.startswith('01') and digits[2] in '3456789':
        return digits
    raise ValidationError('Enter a valid Bangladeshi mobile number (01XXXXXXXXX).')


def validate_nid(value):
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    if len(digits) not in (10, 13, 17):
        raise ValidationError('NID must be 10, 13, or 17 digits.')
    return digits


def birth_registration_warning(value):
    """Return a warning string if the number looks unusual; never hard-fail."""
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    if digits and len(digits) != 17:
        return 'Birth registration numbers in Bangladesh are usually 17 digits.'
    return ''


def process_passport_photo(image_field, filename=None):
    """Validate and store a print-safe JPEG/PNG without GPS EXIF. Returns ContentFile."""
    name = filename or getattr(image_field, 'name', 'photo.jpg')
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_PHOTO_EXTS:
        raise ValidationError('Please upload a JPG or PNG photo (HEIC is not accepted).')

    image_field.seek(0)
    data = image_field.read()
    if len(data) < MIN_PHOTO_BYTES:
        raise ValidationError('Photo is too small. Please upload an image of at least 50 KB.')
    if len(data) > MAX_PHOTO_BYTES:
        raise ValidationError('Photo must be 2 MB or smaller.')

    try:
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:
        raise ValidationError('Could not read the photo. Please upload a valid JPG or PNG.') from exc

    if img.format not in ALLOWED_PHOTO_TYPES and ext not in ALLOWED_PHOTO_EXTS:
        raise ValidationError('Please upload a JPG or PNG photo (HEIC is not accepted).')

    width, height = img.size
    if width < MIN_PHOTO_DIM or height < MIN_PHOTO_DIM:
        raise ValidationError('Photo must be at least 300×300 pixels.')

    img = img.convert('RGB')
    img.thumbnail((MAX_PHOTO_WIDTH, MAX_PHOTO_HEIGHT), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=88, optimize=True)
    buffer.seek(0)
    return ContentFile(buffer.read(), name='photo.jpg')
