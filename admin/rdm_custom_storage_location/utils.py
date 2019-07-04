# -*- coding: utf-8 -*-

from django.http import JsonResponse
from furl import furl
import httplib
import requests
import os
import owncloud

from addons.owncloud import settings as owncloud_settings
from addons.s3 import utils as s3_utils
from addons.swift import utils as swift_utils
from addons.swift.provider import SwiftProvider
from website import settings as osf_settings

providers = None
enabled_providers_list = [
    's3', 'box', 'googledrive', 'osfstorage',
    'nextcloud', 'swift', 'owncloud', 's3compat'
]

def get_providers():
    provider_list = []
    for provider in osf_settings.ADDONS_AVAILABLE:
        if 'storage' in provider.categories and provider.short_name in enabled_providers_list:
            provider.icon_url_admin = \
                '/custom_storage_location/icon/{}/comicon.png'.format(provider.short_name)
            provider.modal_path = get_modal_path(provider.short_name)
            provider_list.append(provider)
    provider_list.sort(key=lambda x: x.full_name.lower())
    return provider_list

def get_addon_by_name(addon_short_name):
    """get Addon object from Short Name."""
    for addon in osf_settings.ADDONS_AVAILABLE:
        if addon.short_name == addon_short_name:
            return addon
    return None

def get_modal_path(short_name):
    base_path = os.path.join('rdm_custom_storage_location', 'providers')
    return os.path.join(base_path, '{}_modal.html'.format(short_name))

def test_s3_connection(access_key, secret_key):
    """Verifies new external account credentials and adds to user's list"""
    if not (access_key and secret_key):
        return JsonResponse({
            'message': 'All the fields above are required.'
        }, status=httplib.BAD_REQUEST)
    user_info = s3_utils.get_user_info(access_key, secret_key)
    if not user_info:
        return JsonResponse({
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid,'
                'and that they have permission to list buckets.')
        }, status=httplib.BAD_REQUEST)

    if not s3_utils.can_list(access_key, secret_key):
        return JsonResponse({
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, status=httplib.BAD_REQUEST)
    s3_response = {
        'id': user_info.id,
        'display_name': user_info.display_name,
        'Owner': user_info.Owner,
    }

    return JsonResponse({
        'message': ('Credentials are valid'),
        'data': s3_response
    }, status=httplib.OK)

def test_owncloud_connection(host_url, username, password, folder):
    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    try:
        oc = owncloud.Client(host.url, verify_certs=owncloud_settings.USE_SSL)
        oc.login(username, password)
        oc.logout()
    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'message': 'Invalid ownCloud server.' + host.url
        }, status=httplib.BAD_REQUEST)
    except owncloud.owncloud.HTTPResponseError:
        return JsonResponse({
            'message': 'ownCloud Login failed.'
        }, status=httplib.UNAUTHORIZED)

    return JsonResponse({
        'message': ('Credentials are valid')
    }, status=httplib.OK)

def test_swift_connection(auth_version, auth_url, access_key, secret_key, tenant_name,
                          user_domain_name, project_domain_name, folder, container):
    """Verifies new external account credentials and adds to user's list"""
    if not (auth_version and auth_url and access_key and secret_key and tenant_name):
        return JsonResponse({
            'message': 'All the fields above are required.'
        }, status=httplib.BAD_REQUEST)
    if auth_version == '3' and not user_domain_name:
        return JsonResponse({
            'message': 'The field `user_domain_name` is required when you choose identity V3.'
        }, status=httplib.BAD_REQUEST)
    if auth_version == '3' and not project_domain_name:
        return JsonResponse({
            'message': 'The field `project_domain_name` is required when you choose identity V3.'
        }, status=httplib.BAD_REQUEST)

    user_info = swift_utils.get_user_info(auth_version, auth_url, access_key,
                                    user_domain_name, secret_key, tenant_name,
                                    project_domain_name)

    if not user_info:
        return JsonResponse({
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list containers.')
        }, status=httplib.BAD_REQUEST)

    if not swift_utils.can_list(auth_version, auth_url, access_key, user_domain_name,
                          secret_key, tenant_name, project_domain_name):
        return JsonResponse({
            'message': ('Unable to list containers.\n'
                'Listing containers is required permission.')
        }, status=httplib.BAD_REQUEST)

    provider = SwiftProvider(account=None, auth_version=auth_version,
                             auth_url=auth_url, tenant_name=tenant_name,
                             project_domain_name=project_domain_name,
                             username=access_key,
                             user_domain_name=user_domain_name,
                             password=secret_key)
    swift_response = {
        'id': provider.account.id,
        'display_name': provider.account.display_name,
    }
    return JsonResponse({
        'message': ('Credentials are valid'),
        'data': swift_response
    }, status=httplib.OK)