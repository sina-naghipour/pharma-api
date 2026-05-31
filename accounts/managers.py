from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Custom user model manager where username is the unique identifier for authentication."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create and save a User with the given username, email and password."""
        if not username:
            raise ValueError(_('The Username must be set'))
        
        # Email is now optional – normalize only if provided
        if email:
            email = self.normalize_email(email)
        else:
            email = ''
        
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create and save a SuperUser with the given username, email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(username, email, password, **extra_fields)