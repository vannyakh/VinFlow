from django import template
from panel.settings_utils import get_setting

register = template.Library()

@register.simple_tag
def get_site_setting(key, default=None):
    """Get a site setting value by key"""
    return get_setting(key, default)

