"""
Middleware for VinFlow Panel
"""
from django.shortcuts import render, redirect
from django.urls import reverse, resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin
from .settings_utils import get_setting_bool, get_setting


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware to check if maintenance mode is enabled.
    If enabled, redirect all users (except admins) to a maintenance page.
    """
    
    def process_request(self, request):
        # Check if maintenance mode is enabled
        maintenance_mode = get_setting_bool('maintenance_mode', default=False)
        
        if not maintenance_mode:
            return None
        
        # Allow static and media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        # Try to resolve the current URL to get the view name
        try:
            resolved = resolve(request.path)
            view_name = resolved.url_name
            
            # Allow access to maintenance page itself to avoid redirect loops
            if view_name == 'maintenance':
                return None
            
            # Allow access to login, logout, and set_language
            if view_name in ['login', 'logout', 'set_language']:
                return None
        except Resolver404:
            pass
        
        # Allow admin users to access the site
        if request.user.is_authenticated:
            try:
                if request.user.is_superuser or request.user.profile.role == 'admin':
                    return None
            except Exception:
                pass
        
        # Redirect to maintenance page
        return redirect('maintenance')

