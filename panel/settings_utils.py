"""
Utility functions for accessing system settings
"""
from .models import SystemSetting

def get_setting(key, default=None):
    """
    Get a setting value by key.
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist
    
    Returns:
        The setting value or default
    """
    try:
        setting = SystemSetting.objects.get(key=key)
        value = setting.get_value()
        return value if value else default
    except SystemSetting.DoesNotExist:
        return default

def get_setting_bool(key, default=False):
    """
    Get a boolean setting value.
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist
    
    Returns:
        Boolean value
    """
    try:
        setting = SystemSetting.objects.get(key=key)
        return setting.get_bool_value()
    except SystemSetting.DoesNotExist:
        return default

def get_setting_int(key, default=0):
    """
    Get an integer setting value.
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist
    
    Returns:
        Integer value
    """
    try:
        setting = SystemSetting.objects.get(key=key)
        return setting.get_int_value()
    except SystemSetting.DoesNotExist:
        return default

def get_setting_float(key, default=0.0):
    """
    Get a float setting value.
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist
    
    Returns:
        Float value
    """
    try:
        setting = SystemSetting.objects.get(key=key)
        return setting.get_float_value()
    except SystemSetting.DoesNotExist:
        return default

def set_setting(key, value, user=None):
    """
    Set a setting value.
    
    Args:
        key: The setting key
        value: The value to set
        user: User making the change (optional)
    
    Returns:
        The SystemSetting object
    """
    setting, created = SystemSetting.objects.get_or_create(
        key=key,
        defaults={'label': key.replace('_', ' ').title(), 'value': str(value)}
    )
    setting.value = str(value)
    if user:
        setting.updated_by = user
    setting.save()
    return setting

def get_setting_image(key, default=None):
    """
    Get an image setting value (returns image path/URL).
    
    Args:
        key: The setting key
        default: Default value if setting doesn't exist
    
    Returns:
        Image path/URL or default
    """
    return get_setting(key, default)

def get_setting_image_list(key, default=None):
    """
    Get an image list setting value (returns list of image paths).
    
    Args:
        key: The setting key
        default: Default list if setting doesn't exist
    
    Returns:
        List of image paths or default
    """
    try:
        setting = SystemSetting.objects.get(key=key)
        return setting.get_image_list()
    except SystemSetting.DoesNotExist:
        return default if default is not None else []

