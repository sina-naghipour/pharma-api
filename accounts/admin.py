from django.contrib import admin
from django.contrib.auth.hashers import make_password
from unfold.admin import ModelAdmin
from .models import User, UserProfile, UserAddress, PharmacyLicense

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    inlines = (UserProfileInline,)
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'is_verified')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'user_type'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and form.cleaned_data.get('password1'):
            obj.password = make_password(form.cleaned_data['password1'])
        super().save_model(request, obj, form, change)

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'gender', 'date_of_birth', 'created_at')
    list_filter = ('gender', 'newsletter_subscription', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')

@admin.register(UserAddress)
class UserAddressAdmin(ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'city', 'address_type', 'is_default')
    list_filter = ('address_type', 'is_default', 'country')
    search_fields = ('user__username', 'first_name', 'last_name', 'city')

@admin.register(PharmacyLicense)
class PharmacyLicenseAdmin(ModelAdmin):
    list_display = ('pharmacy_name', 'license_number', 'user', 'status', 'license_expiry_date')
    list_filter = ('status', 'license_expiry_date', 'created_at')
    search_fields = ('pharmacy_name', 'license_number', 'user__username')
    readonly_fields = ('created_at', 'updated_at')