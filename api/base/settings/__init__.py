# -*- coding: utf-8 -*-
'''Consolidates settings from defaults.py and local.py.

::
    >>> from api.base import settings
    >>> settings.API_BASE
    'v2/'
'''
import warnings

from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError as error:
    warnings.warn('No api/base/settings/local.py settings file found. Did you remember to '
                  'copy local-dist.py to local.py?', ImportWarning)

if not DEBUG:
    from . import local
    from . import defaults
    for setting in ('JWE_SECRET', 'JWT_SECRET'):
        assert getattr(local, setting, None) and getattr(local, setting, None) != getattr(defaults, setting, None), '{} must be specified in local.py when DEV_MODE is False'.format(setting)
