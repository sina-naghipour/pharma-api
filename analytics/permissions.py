# analytics/permissions.py
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners or admins to access objects.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin permissions
        if request.user.is_staff:
            return True
        
        # Check if object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object has a dashboard attribute with user
        if hasattr(obj, 'dashboard') and hasattr(obj.dashboard, 'user'):
            return obj.dashboard.user == request.user
        
        return False


class IsCreatorOrAdmin(permissions.BasePermission):
    """
    Permission to only allow creators or admins to access objects.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin permissions
        if request.user.is_staff:
            return True
        
        # Check if object has a created_by attribute
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class IsReportAccessible(permissions.BasePermission):
    """
    Permission to check if a user can access a report.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin permissions
        if request.user.is_staff:
            return True
        
        # Creator permissions
        if obj.created_by == request.user:
            return True
        
        # Public report
        if obj.is_public:
            return True
        
        # Shared with user
        if request.user in obj.shared_with.all():
            return True
        
        return False