from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Verify that the PostgreSQL vector extension is enabled.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            enabled = cursor.fetchone()[0]

        if not enabled:
            raise CommandError('The PostgreSQL vector extension is not enabled.')

        self.stdout.write(self.style.SUCCESS('PostgreSQL vector extension is enabled.'))
