"""
Routes associated with the niirdccore addon
"""

from framework.routing import Rule, json_renderer
from . import SHORT_NAME
from . import views

api_routes = {
    'rules': [
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'post', views.niirdccore_set_config, json_renderer),
        Rule([
            '/project/<pid>/{}/dmp'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/dmp'.format(SHORT_NAME),
        ], 'get', views.niirdccore_get_dmp_info, json_renderer),
        Rule([
            '/project/{}/dmp_notification'.format(SHORT_NAME),
        ], 'post', views.niirdccore_dmp_notification, json_renderer),
    ],
    'prefix': '/api/v1',
}
