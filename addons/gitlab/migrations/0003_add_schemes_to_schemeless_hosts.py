# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-16 18:14
from __future__ import unicode_literals

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

def add_http_scheme_to_gitlab_host(apps, schema_editor):
    ExternalAccount = apps.get_model('osf', 'ExternalAccount')
    gitlab_accounts = ExternalAccount.objects.filter(provider='gitlab')
    for gitlab_account in gitlab_accounts:
        if not gitlab_account.oauth_secret.startswith('https://'):
            gitlab_account.oauth_secret = 'https://{}'.format(gitlab_account.oauth_secret)
            gitlab_account.save()


def revert_add_http_scheme_to_gitlab_host(apps, schema_editor):
    logger.warning('No reverse migration for 0003_add_schemes_to_schemeless_hosts.py because we can\'t identify'
                  ' hostnames that were contained schemes before the initial migration.')

class Migration(migrations.Migration):

    dependencies = [
        ('addons_gitlab', '0002_auto_20171121_1426'),
    ]

    operations = [
        migrations.RunPython(add_http_scheme_to_gitlab_host, revert_add_http_scheme_to_gitlab_host)
    ]
