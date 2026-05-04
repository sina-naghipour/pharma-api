# payments/permissions.py
from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners of an object or admins to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user.is_staff:
            return True
        
        # Check if object has user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object has payment with user field
        if hasattr(obj, 'payment') and hasattr(obj.payment, 'user'):
            return obj.payment.user == request.user
        
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow admins to modify, but allow read access to all.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff