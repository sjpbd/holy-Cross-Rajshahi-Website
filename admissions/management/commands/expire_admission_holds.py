from django.core.management.base import BaseCommand

from admissions.services import expire_old_drafts, expire_slot_holds


class Command(BaseCommand):
    help = 'Release expired viva slot holds and expire old unpaid drafts.'

    def handle(self, *args, **options):
        holds = expire_slot_holds()
        drafts = expire_old_drafts()
        self.stdout.write(self.style.SUCCESS(
            f'Released {holds} expired slot hold(s); expired {drafts} draft(s).'
        ))
