"""Load the demo members, libraries and packs, offline (packs.demo.seed_demo()).

    uv run python manage.py seed_demo

Safe to run again: it adds only what's missing and puts the demo packs back.
"""

from django.core.management.base import BaseCommand

from packs.demo import DEMO_PASSWORD, seed_demo


class Command(BaseCommand):
    help = "Load the demo members, their libraries and public packs from the offline snapshot."

    def handle(self, *args, **options):
        report = seed_demo()
        self.stdout.write(
            f"Created {report.users} users, {report.assets} assets, {report.entries} library "
            f"entries, {report.packs} packs and {report.items} pack items "
            "(anything already there was kept)."
        )
        names = ", ".join(report.usernames)
        self.stdout.write(
            self.style.SUCCESS(f"Sign in as {names}, each with the password {DEMO_PASSWORD}.")
        )
