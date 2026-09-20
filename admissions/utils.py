# admissions/utils.py
import re
from io import BytesIO
from pathlib import Path

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .constants import CACHE_SKIP_PREFIXES

BENGALI_ERROR = 'শুধু বাংলা অক্ষরে লিখুন / Use Bengali characters only.'
BIRTH_REG_LENGTHS = (13, 16, 17)
BIRTH_REG_ERROR = 'Birth registration number must be 13, 16, or 17 digits.'
PHONE_ERROR = 'Phone number must be 11 digits (01XXXXXXXXX).'
_HAS_BENGALI = re.compile(r'[\u0980-\u09FF]')
_HAS_LATIN = re.compile(r'[A-Za-z]')
_BENGALI_ALLOWED = re.compile(r'^[\u0980-\u09FF\s।॥\-–.,()]+$')

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
    raise ValidationError(PHONE_ERROR)


def validate_nid(value):
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    if len(digits) not in (10, 13, 17):
        raise ValidationError('NID must be 10, 13, or 17 digits.')
    return digits


def validate_birth_registration(value):
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    if len(digits) not in BIRTH_REG_LENGTHS:
        raise ValidationError(BIRTH_REG_ERROR)
    return digits


def validate_bengali_text(value):
    text = (value or '').strip()
    if not text:
        raise ValidationError('This field is required.')
    if _HAS_LATIN.search(text) or not _HAS_BENGALI.search(text) or not _BENGALI_ALLOWED.match(text):
        raise ValidationError(BENGALI_ERROR)
    return text


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
