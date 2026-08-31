# -*- coding: utf-8 -*-
"""D-125: management command — import سrnх-ha az snapshot talil lag.

استفاده:
    python manage.py import_log_leads [path]
    python manage.py import_log_leads /tmp/rihan_analytics.json
"""
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from src.modules.leads.analytics import import_from_snapshot


class Command(BaseCommand):
    help = 'Import VisitorLead-ha az snapshot-e tahil-e log-e nginx (JSON)'

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', default='/tmp/rihan_analytics.json')

    def handle(self, *args, **opts):
        path = opts['path']
        try:
            stats = import_from_snapshot(path)
        except FileNotFoundError:
            raise CommandError(f'Snapshot peyda nashod: {path}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Snapshot morde: {e}')
        self.stdout.write(self.style.SUCCESS(
            "IMPORT OK | visitors: {visitors} | created: {created} | updated: {updated} | "
            "converted: {converted} | hot: {hot}".format(**stats)
        ))
