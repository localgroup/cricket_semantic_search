import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from ingestion.service import ingest_file

class Command(BaseCommand):
    help = "Parse cricket_log.txt and upsert event records into MongoDB and Qdrant."
    def add_arguments(self, parser):
        parser.add_argument("--file", default=os.getenv("INPUT_FILE", "data/cricket_log.txt"))
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.is_file():
            raise CommandError(f"Input file not found: {path}")
        try:
            result = ingest_file(path)
        except Exception as exc:
            raise CommandError(f"Ingestion failed: {exc}") from exc
        for key, value in result.items():
            self.stdout.write(f"{key}: {value}")
