# -*- coding: utf-8 -*-
from rest_framework import status as http_status
from flask import request
import logging
import requests

from . import SHORT_NAME
from . import settings
from framework.exceptions import HTTPError
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_have_addon,
)
from addons.jupyterhub.apps import JupyterhubAddonAppConfig
from addons.niirdccore.models import AddonList

logger = logging.getLogger(__name__)

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def niirdccore_set_config(**kwargs):

    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)

    try:
        dmp_id = request.json['dmp']['redboxOid']
        dmp_metadata = request.json['dmp']['metadata']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # save dmp_id
    addon.set_dmp_id(dmp_id)

    # provisioning
    dataAnalysisResources = dmp_metadata.get("vivo:Dataset_redbox:DataAnalysisResources")

    if dataAnalysisResources == JupyterhubAddonAppConfig.full_name \
        or dataAnalysisResources ==  JupyterhubAddonAppConfig.short_name:

        # add jupyterHub
        node.add_addon(JupyterhubAddonAppConfig.short_name, auth=None, log=False)
    else:
        return {"result": "jupyterhub none"}

    return {"result": "jupyterhub added"}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def niirdccore_get_dmp_info(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)

    dmp_id = addon.get_dmp_id()
    url = settings.DMR_URL + '/v1/dmp/' + str(dmp_id)
    headers = {'Authorization': 'Bearer ' + addon.get_dmr_api_key()}
    dmp_info = requests.get(url, headers=headers)

    return {'data': {'id': node._id, 'type': 'dmp-status',
                    'attributes': dmp_info.text}}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def niirdccore_apply_dmp_subscribe(**kwargs):
    node = kwargs['node']

    addon_list = AddonList()

    addon_list.set_addon_id(kwargs['addon_id'])
    addon_list.set_callback(kwargs['callback'])
    addon_list.set_owner(node.get_addon(SHORT_NAME))

    return
