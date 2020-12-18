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
    ],
    'prefix': '/api/v1',
}
