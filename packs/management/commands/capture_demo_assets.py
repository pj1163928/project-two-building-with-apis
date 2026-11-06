"""Capture the demo snapshot (packs/demo_assets.json): run once, by hand, online.

    uv run python manage.py capture_demo_assets

It calls each provider's fetch_record() for every asset packs.demo names and
writes the records to the snapshot, which is committed so seed_demo works
offline. It writes nothing unless every asset was fetched. The tests never
run it against a live provider.
"""

import time

from django.core.management.base import BaseCommand, CommandError

from packs.demo import SNAPSHOT_PATH, demo_asset_refs, write_snapshot
from providers import PROVIDERS_BY_KEY, ProviderError

# Openverse lets anonymous clients make 20 requests a minute, so its fetches are spaced out.
PAUSE_SECONDS = {"openverse": 3.5}


class Command(BaseCommand):
    help = "Fetch every demo asset from its provider and write the seed_demo snapshot (online)."

    def handle(self, *args, **options):
        records, failures = [], []
        refs = demo_asset_refs()
        for number, (provider_key, external_id) in enumerate(refs, start=1):
            provider = PROVIDERS_BY_KEY[provider_key]
            self.stdout.write(f"[{number}/{len(refs)}] {provider.NAME} {external_id}")
            try:
                records.append(provider.fetch_record(external_id))
            except ProviderError as error:
                failures.append(f"{provider.NAME} {external_id}: {error}")
            time.sleep(PAUSE_SECONDS.get(provider_key, 0))
        if failures:
            raise CommandError(
                "Nothing written. These assets couldn't be fetched:\n" + "\n".join(failures)
            )
        write_snapshot(records)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(records)} assets to {SNAPSHOT_PATH}."))
