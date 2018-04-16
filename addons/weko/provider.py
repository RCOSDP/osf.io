# -*- coding: utf-8 -*-

from osf.models.external import BasicAuthProviderMixin


class WEKOProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'WEKO'
    short_name = 'weko'

    def __init__(self, account=None, sword_url=None, username=None,
                 password=None):
        return super(WEKOProvider, self).__init__(account=account,
                                                   host=sword_url,
                                                   username=username,
                                                   password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )

    @property
    def sword_url(self):
        return self.host
