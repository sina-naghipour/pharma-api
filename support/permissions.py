# support/permissions.py
from rest_framework import permissions


class IsOwnerOrStaffOrReadOnly(permissions.BasePermission):
    """
    Allow read access to everyone, but only allow write access to the owner or staff.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner or staff
        return obj.user == request.user or request.user.is_staff


class IsStaffOrCreateOnly(permissions.BasePermission):
    """
    Allow create access to everyone, but only allow other actions to staff.
    """
    
    def has_permission(self, request, view):
        # Create permissions are allowed to any authenticated request
        if view.action == 'create':
            return request.user.is_authenticated
        
        # List permission depends on the action
        if view.action in ['list', 'retrieve']:
            return True
            
        # Other permissions are only allowed to staff
        return request.user.is_staff


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Allow access only to the owner or staff.
    """
    
    def has_object_permission(self, request, view, obj):
        # Allow staff access
        if request.user.is_staff:
            return True
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
            
        # Check if user is the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False