# accounts/permissions.py
from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions are only allowed to the owner of the object or admin
        if hasattr(obj, 'user'):
            return obj.user == request.user or request.user.is_staff
        
        # If object is the user itself
        return obj == request.user or request.user.is_staff

class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Check if object has user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # If object is the user itself
        return obj == request.user

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit, but allow read access to authenticated users.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        return request.user.is_staff

class IsPharmacyUser(permissions.BasePermission):
    """
    Custom permission for pharmacy users only.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'pharmacy'

class IsDoctorUser(permissions.BasePermission):
    """
    Custom permission for doctor users only.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'doctor'