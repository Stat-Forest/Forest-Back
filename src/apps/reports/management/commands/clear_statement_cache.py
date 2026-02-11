# apps/reports/management/commands/clear_statement_cache.py
"""
Management command to manually clear statement cache
Usage: python manage.py clear_statement_cache
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Clear all statement-related cache'

    def handle(self, *args, **options):
        deleted_count = cache.delete_pattern("statement_list:*")
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully cleared statement cache. Deleted {deleted_count} keys.'
            )
        )