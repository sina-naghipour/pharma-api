# orders/permissions.py
from rest_framework import permissions


class IsOrderOwner(permissions.BasePermission):
    """
    Allow access only to order owners or staff.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Allow staff to access any order
        if request.user.is_staff:
            return True
        
        # Allow users to access only their own orders
        return obj.user == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read access to authenticated users, but only write access to admin users.
    """
    
    def has_permission(self, request, view):
        # Allow read-only access for authenticated users
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated:
            return True
        
        # Write permissions are only allowed to admin users
        return request.user and request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to authenticated users
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated:
            return True
        
        # Write permissions are only allowed to admin users
        return request.user and request.user.is_staff