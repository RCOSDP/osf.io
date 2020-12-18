# -*- coding: utf-8 -*-
from rest_framework import status as http_status
from flask import request
import logging

from . import SHORT_NAME
from . import settings
from framework.exceptions import HTTPError
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_have_addon,
)
from addons.jupyterhub.apps import JupyterhubAddonAppConfig

logger = logging.getLogger(__name__)

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def niirdccore_set_config(**kwargs):

    node = kwargs['node'] or kwargs['project']

    try:
        dmp = request.json['dmp']['metadata']

    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    dataAnalysisResources = dmp.get("vivo:Dataset_redbox:DataAnalysisResources")

    if dataAnalysisResources == JupyterhubAddonAppConfig.full_name \
        or dataAnalysisResources ==  JupyterhubAddonAppConfig.short_name:

        # add jupyterHub
        node.add_addon(JupyterhubAddonAppConfig.short_name, auth=None, log=False)
    else:
        return {"result": "jupyterhub none"}

    return {"result": "jupyterhub added"}


