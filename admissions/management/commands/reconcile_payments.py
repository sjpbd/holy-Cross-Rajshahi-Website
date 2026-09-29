from django.core.management.base import BaseCommand

from admissions.payments import reconcile_pending_payments


class Command(BaseCommand):
    help = 'Re-verify pending JanataPay payments with the bank and confirm or fail them.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-age', type=int, default=5,
            help='Only check attempts at least this many minutes old (default 5).',
        )
        parser.add_argument(
            '--max-age', type=int, default=48,
            help='Stop checking attempts older than this many hours; they are marked expired (default 48).',
        )

    def handle(self, *args, **options):
        counts = reconcile_pending_payments(
            min_age_minutes=options['min_age'],
            max_age_hours=options['max_age'],
        )
        self.stdout.write(self.style.SUCCESS(
            'Checked {checked}: {paid} paid, {failed} failed/cancelled, {pending} still pending, '
            '{errors} error(s); {expired} expired.'.format(**counts)
        ))
