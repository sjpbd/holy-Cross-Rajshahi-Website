import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from admissions.janatapay import JanataPayClient, JanataPayError


class Command(BaseCommand):
    help = 'Check JanataPay credentials and encryption against the configured gateway.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tokenize', type=int, metavar='AMOUNT',
            help='Also create a test transaction for AMOUNT taka and print its payment URL.',
        )

    def handle(self, *args, **options):
        client = JanataPayClient()
        self.stdout.write(f'Gateway: {settings.JANATAPAY_BASE_URL}  (PAYMENT_GATEWAY={settings.PAYMENT_GATEWAY})')
        try:
            client.check_configured()
            access_token, _aes_key, expires_at = client.authenticate()
        except JanataPayError as exc:
            raise CommandError(f'Authentication failed: {exc}')
        self.stdout.write(self.style.SUCCESS(f'Authentication OK. Token expires at {expires_at:%Y-%m-%d %H:%M:%S %Z}.'))

        amount = options.get('tokenize')
        if not amount:
            return
        reference_id = f'HCTEST{uuid.uuid4().hex[:10].upper()}'
        try:
            result = client.tokenize(amount, reference_id, 'Holy Cross connectivity test')
            status = client.verify(reference_id, result['transaction_token'])
        except JanataPayError as exc:
            raise CommandError(f'Tokenize/verify failed: {exc}')
        self.stdout.write(self.style.SUCCESS('Tokenize OK.'))
        self.stdout.write(f'  Reference ID : {reference_id}')
        self.stdout.write(f'  Payment URL  : {result["payment_url"]}')
        self.stdout.write(f'  Verify status: {status["status_code"]} {status["status"]} (amount {status["amount"]})')
        self.stdout.write('Open the payment URL in a browser to try a sandbox payment. '
                          'This test transaction is not linked to any application.')
