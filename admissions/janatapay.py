# admissions/janatapay.py
"""JanataPay (Janata Bank) payment gateway API client.

Wire format, confirmed against the sandbox:
- Auth body: {"merchant": b64(uid), "key": RSA-OAEP-SHA256(b64 AES key), "data": AES-GCM(payload)}
- Tokenize / verify body: {"merchant": b64(uid), "accessToken": token, "data": AES-GCM(payload)}
- AES ciphertext = base64(IV[12] + ciphertext + tag[16]).
- The AES key is bound to the access token: both must come from the same auth call.
"""
import base64
import json
import logging
import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

import requests
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

AUTH_PATH = '/jbagg/api/auth'
TOKENIZE_PATH = '/jbagg/api/transaction/tokenize'
VERIFY_PATH = '/jbagg/api/transaction/verify'

STATUS_INITIATED = '1001'
STATUS_SENT_TO_PGW = '1002'
STATUS_SUCCESS = '1003'
STATUS_FAILED = '1004'
STATUS_CANCELED = '1005'
STATUS_REFUNDED = '1007'
PENDING_CODES = {STATUS_INITIATED, STATUS_SENT_TO_PGW}

TOKEN_SAFETY_MARGIN = timedelta(seconds=30)
DEFAULT_TOKEN_LIFETIME = timedelta(minutes=4)

AUTH_ERROR_HINTS = ('jwt', 'token', 'expired', 'tag mismatch', 'unauthor')


class JanataPayError(Exception):
    """Any failure talking to the gateway (network, HTTP, crypto or business error)."""


class JanataPayAuthError(JanataPayError):
    """The access token was rejected; the caller should re-authenticate."""


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------

def generate_aes_key():
    return os.urandom(32)


def aes_encrypt(plaintext, key):
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')
    iv = os.urandom(12)
    return base64.b64encode(iv + AESGCM(key).encrypt(iv, plaintext, None)).decode('ascii')


def aes_decrypt(token, key):
    raw = base64.b64decode(token)
    if len(raw) < 12 + 16:
        raise JanataPayError('Encrypted payload is too short.')
    try:
        return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode('utf-8')
    except InvalidTag as exc:
        raise JanataPayError('Could not decrypt gateway response (tag mismatch).') from exc


def public_key_pem(raw_key):
    """Wrap the bank's raw Base64 key as PEM text without decoding it first."""
    body = ''.join((raw_key or '').split())
    if body.startswith('-----BEGIN'):
        return body
    lines = [body[i:i + 64] for i in range(0, len(body), 64)]
    return '-----BEGIN PUBLIC KEY-----\n' + '\n'.join(lines) + '\n-----END PUBLIC KEY-----\n'


def rsa_encrypt_key(aes_key_b64, raw_public_key):
    public_key = serialization.load_pem_public_key(public_key_pem(raw_public_key).encode('ascii'))
    encrypted = public_key.encrypt(
        aes_key_b64.encode('ascii'),
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    return base64.b64encode(encrypted).decode('ascii')


def _jwt_expiry(token):
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get('exp')
        if exp:
            return datetime.fromtimestamp(int(exp), tz=dt_timezone.utc)
    except (IndexError, ValueError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class JanataPayClient:
    def __init__(self, base_url=None, username=None, password=None, merchant_uid=None,
                 public_key=None, timeout=None, session=None):
        self.base_url = (base_url or settings.JANATAPAY_BASE_URL).rstrip('/')
        self.username = username or settings.JANATAPAY_USERNAME
        self.password = password or settings.JANATAPAY_PASSWORD
        self.merchant_uid = merchant_uid or settings.JANATAPAY_MERCHANT_UID
        self.public_key = public_key or settings.JANATAPAY_PUBLIC_KEY
        self.timeout = timeout or settings.JANATAPAY_TIMEOUT
        self.http = session or requests.Session()

    def check_configured(self):
        missing = [
            name for name, value in (
                ('JANATAPAY_USERNAME', self.username),
                ('JANATAPAY_PASSWORD', self.password),
                ('JANATAPAY_MERCHANT_UID', self.merchant_uid),
                ('JANATAPAY_PUBLIC_KEY', self.public_key),
            ) if not value
        ]
        if missing:
            raise JanataPayError(f'JanataPay is not configured: missing {", ".join(missing)}.')

    @property
    def merchant_b64(self):
        return base64.b64encode(self.merchant_uid.encode('utf-8')).decode('ascii')

    def _post(self, path, body):
        url = f'{self.base_url}{path}'
        try:
            response = self.http.post(url, json=body, timeout=self.timeout)
        except requests.RequestException as exc:
            raise JanataPayError(f'Could not reach JanataPay: {exc.__class__.__name__}') from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise JanataPayError(f'JanataPay returned HTTP {response.status_code} with a non-JSON body.') from exc
        status_code = data.get('statusCode')
        if response.status_code >= 400 or (status_code and int(status_code) >= 400):
            message = str(data.get('statusMessage') or f'HTTP {response.status_code}')
            if path != AUTH_PATH and any(hint in message.lower() for hint in AUTH_ERROR_HINTS):
                raise JanataPayAuthError(message)
            raise JanataPayError(f'JanataPay error: {message}')
        return data

    # -- authentication ----------------------------------------------------

    def authenticate(self):
        """Log in and return (access_token, aes_key_bytes, expires_at). Not cached."""
        self.check_configured()
        aes_key = generate_aes_key()
        aes_key_b64 = base64.b64encode(aes_key).decode('ascii')
        payload = {
            'merchantUid': self.merchant_uid,
            'merchantUsername': self.username,
            'merchantPassword': self.password,
            'aesKey': aes_key_b64,
        }
        body = {
            'merchant': self.merchant_b64,
            'key': rsa_encrypt_key(aes_key_b64, self.public_key),
            'data': aes_encrypt(json.dumps(payload), aes_key),
        }
        data = self._post(AUTH_PATH, body)
        if not data.get('data'):
            raise JanataPayError(f'JanataPay auth failed: {data.get("statusMessage") or "empty response"}')
        decrypted = json.loads(aes_decrypt(data['data'], aes_key))
        access_token = decrypted.get('accessToken')
        if not access_token:
            raise JanataPayError('JanataPay auth response did not include an access token.')
        expires_at = _jwt_expiry(access_token) or (timezone.now() + DEFAULT_TOKEN_LIFETIME)
        return access_token, aes_key, expires_at

    def get_session(self, force_refresh=False):
        """Return a cached (access_token, aes_key) shared by all processes via the database."""
        from .models import GatewayAuthToken

        with transaction.atomic():
            record, _ = GatewayAuthToken.objects.select_for_update().get_or_create(gateway='janatapay')
            valid = (
                record.access_token
                and record.aes_key
                and record.expires_at
                and record.expires_at - TOKEN_SAFETY_MARGIN > timezone.now()
            )
            if valid and not force_refresh:
                return record.access_token, base64.b64decode(record.aes_key)
            access_token, aes_key, expires_at = self.authenticate()
            record.access_token = access_token
            record.aes_key = base64.b64encode(aes_key).decode('ascii')
            record.expires_at = expires_at
            record.save()
            return access_token, aes_key

    def _call(self, path, build_payload):
        """POST an encrypted payload; re-authenticate once if the token is rejected."""
        for attempt in range(2):
            access_token, aes_key = self.get_session(force_refresh=attempt > 0)
            payload = build_payload(access_token)
            body = {
                'merchant': self.merchant_b64,
                'accessToken': access_token,
                'data': aes_encrypt(json.dumps(payload), aes_key),
            }
            try:
                data = self._post(path, body)
            except JanataPayAuthError:
                if attempt == 0:
                    logger.info('JanataPay token rejected; re-authenticating.')
                    continue
                raise
            if not data.get('data'):
                raise JanataPayError(f'JanataPay returned no data: {data.get("statusMessage") or "unknown"}')
            return json.loads(aes_decrypt(data['data'], aes_key)), aes_key
        raise JanataPayError('JanataPay authentication failed.')

    # -- API calls -----------------------------------------------------------

    def tokenize(self, amount, reference_id, description, currency=None):
        """Create a payment session. Returns dict with payment_url, transaction_token, aes_key."""
        amount = int(amount)
        currency = currency or settings.JANATAPAY_CURRENCY

        def build(access_token):
            return {
                'merchantUid': self.merchant_uid,
                'amount': amount,
                'currency': currency,
                'description': description[:200],
                'referenceId': reference_id,
                'accessToken': access_token,
            }

        result, aes_key = self._call(TOKENIZE_PATH, build)
        payment_url = result.get('paymentUrl') or result.get('url')
        transaction_token = result.get('transactionToken')
        if not payment_url or not transaction_token:
            raise JanataPayError('JanataPay tokenize response is missing the payment URL or token.')
        return {
            'payment_url': payment_url,
            'transaction_token': transaction_token,
            'expires': result.get('expires', ''),
            'aes_key': base64.b64encode(aes_key).decode('ascii'),
        }

    def verify(self, reference_id, transaction_token):
        """Return dict with status_code, status, amount (Decimal or None), ft_number, raw."""

        def build(access_token):
            return {
                'merchantUid': self.merchant_uid,
                'referenceId': reference_id,
                'transactionToken': transaction_token,
                'accessToken': access_token,
            }

        result, _aes_key = self._call(VERIFY_PATH, build)
        inner = result.get('data') if isinstance(result.get('data'), dict) else {}
        amount = inner.get('amount')
        try:
            amount = Decimal(str(amount)) if amount is not None else None
        except ArithmeticError:
            amount = None
        return {
            'status_code': str(inner.get('transactionStatusCode') or ''),
            'status': str(inner.get('transactionStatus') or result.get('statusMessage') or ''),
            'amount': amount,
            'ft_number': str(inner.get('ftNumber') or ''),
            'payment_gateway': str(inner.get('paymentGateway') or ''),
            'raw': result,
        }
