# accounts/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from .managers import UserManager

class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model"""
    USER_TYPES = [
        ('customer', 'Customer'),
        ('pharmacy', 'Pharmacy'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    ]
    
    # اضافه کردن فیلد username
    username = models.CharField(
        max_length=150, 
        unique=True,
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        validators=[RegexValidator(
            regex=r'^[\w.@+-]+$',
            message='Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.'
        )],
        error_messages={
            'unique': "A user with that username already exists.",
        },
    )
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_pharmacy(self):
        return self.user_type == 'pharmacy'
    
    @property
    def is_doctor(self):
        return self.user_type == 'doctor'


class UserProfile(models.Model):
    """Extended user profile information"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Medical information
    medical_conditions = models.TextField(blank=True, help_text="List of medical conditions")
    allergies = models.TextField(blank=True, help_text="List of known allergies")
    current_medications = models.TextField(blank=True, help_text="Current medications")
    
    # Preferences
    newsletter_subscription = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    
    # Professional information (for doctors/pharmacists)
    license_number = models.CharField(max_length=50, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    hospital_clinic_name = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None


class UserAddress(models.Model):
    """User addresses for shipping and billing"""
    ADDRESS_TYPES = [
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
        ('both', 'Both'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='shipping')
    
    # Address fields
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.CharField(max_length=100, blank=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Address'
        verbose_name_plural = 'User Addresses'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'address_type']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.city}, {self.state_province}"
    
    def get_full_address(self):
        """Return formatted full address"""
        address_parts = [
            f"{self.first_name} {self.last_name}",
            self.company,
            self.address_line_1,
            self.address_line_2,
            f"{self.city}, {self.state_province} {self.postal_code}",
            self.country
        ]
        return '\n'.join([part for part in address_parts if part])
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per type per user
        if self.is_default:
            UserAddress.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class PharmacyLicense(models.Model):
    """Pharmacy license information for pharmacy users"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pharmacy_license')
    
    # License information
    license_number = models.CharField(max_length=100, unique=True)
    pharmacy_name = models.CharField(max_length=200)
    pharmacy_address = models.TextField()
    license_issued_date = models.DateField()
    license_expiry_date = models.DateField()
    issuing_authority = models.CharField(max_length=200)
    
    # Contact information
    pharmacy_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    pharmacy_email = models.EmailField()
    
    # License documents
    license_document = models.FileField(upload_to='licenses/', help_text="Upload license document")
    additional_documents = models.FileField(upload_to='licenses/additional/', blank=True, null=True)
    
    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_licenses'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Additional information
    dea_number = models.CharField(max_length=50, blank=True, help_text="DEA registration number")
    npi_number = models.CharField(max_length=50, blank=True, help_text="National Provider Identifier")
    pharmacy_type = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Type of pharmacy (retail, hospital, etc.)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pharmacy License'
        verbose_name_plural = 'Pharmacy Licenses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['status']),
            models.Index(fields=['license_expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.pharmacy_name} - {self.license_number}"
    
    @property
    def is_expired(self):
        """Check if license is expired"""
        return self.license_expiry_date < timezone.now().date()
    
    @property
    def is_valid(self):
        """Check if license is valid (approved and not expired)"""
        return self.status == 'approved' and not self.is_expired
    
    def days_until_expiry(self):
        """Calculate days until license expires"""
        if self.license_expiry_date:
            today = timezone.now().date()
            delta = self.license_expiry_date - today
            return delta.days
        return None