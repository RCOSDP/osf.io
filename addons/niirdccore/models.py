# -*- coding: utf-8 -*-
import logging
import json

from django.db import models
from django.db.models import Subquery
from django.db.models.signals import post_save
from django.dispatch import receiver

from osf.models import Contributor, RdmAddonOption, AbstractNode
from osf.models.node import Node

from . import settings
from . import SHORT_NAME
from addons.base.models import BaseNodeSettings
from website import settings as ws_settings

logger = logging.getLogger(__name__)

class NodeSettings(BaseNodeSettings):
    """
    プロジェクトにアタッチされたアドオンに関するモデルを定義する。
    """
    @receiver(post_save, sender=Node)
    def add_niirdccore_addon(sender, instance, created, **kwargs):
        if SHORT_NAME not in ws_settings.ADDONS_AVAILABLE_DICT:
            return

        if instance.has_addon(SHORT_NAME):
            # add済みの場合は終了
            return

        inst_ids = instance.affiliated_institutions.values('id')
        addon_option = RdmAddonOption.objects.filter(
            provider=SHORT_NAME,
            institution_id__in=Subquery(inst_ids),
            management_node__isnull=False,
            is_allowed=True
        ).first()
        if addon_option is None:
            return
        if addon_option.organizational_node is not None and \
                not addon_option.organizational_node.is_contributor(instance.creator):
            return

        instance.add_addon(SHORT_NAME, auth=None, log=False)

    def get_dmr_api_key(self):
        return settings.DMR_API_KEY
