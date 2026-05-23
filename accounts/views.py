# accounts/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken import serializers as auth_serializers
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserProfile, UserAddress, PharmacyLicense, OTP
from .serializers import (
    UserSerializer, UserCreateSerializer, UserProfileSerializer,
    UserAddressSerializer, PharmacyLicenseSerializer, PasswordChangeSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    UserLoginSerializer
)
from django.core.cache import cache
from .permissions import IsOwnerOrAdmin
from .otp_service import send_verification_code
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Instantiates and returns the list of permissions that this view requires."""
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [IsOwnerOrAdmin]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Create a new user account"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create auth token
        token, created = Token.objects.get_or_create(user=user)
        
        # Send welcome email
        self.send_welcome_email(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'Account created successfully'
        }, status=status.HTTP_201_CREATED)
    
    def send_welcome_email(self, user):
        """Send welcome email to new user"""
        try:
            subject = 'Welcome to Pharma API'
            message = f"""
            Dear {user.first_name or user.username},
            
            Welcome to Pharma API! Your account has been created successfully.
            
            Username: {user.username}
            
            You can now start exploring our pharmaceutical products and services.
            
            Best regards,
            Pharma API Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user's profile"""
        serializer = self.get_serializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user's password"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Update auth token
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        
        return Response({
            'message': 'Password changed successfully',
            'token': token.key
        })
        
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def password_reset(self, request):
        """Request password reset – with 2‑minute cooldown"""
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data.get('email') or serializer.validated_data.get('username')
        # Normalize identifier: email -> lowercase, username unchanged
        canonical_identifier = identifier.lower() if '@' in identifier else identifier

        cooldown_seconds = 120  # 2 minutes
        cache_key = f'pwd_reset_cooldown_{canonical_identifier}'

        # Check cooldown
        last_request = cache.get(cache_key)
        if last_request:
            elapsed = (timezone.now() - last_request).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return Response({
                    'error': f'لطفاً {remaining} ثانیه دیگر صبر کنید.',
                    'remaining_seconds': remaining
                }, status=status.HTTP_400_BAD_REQUEST)

        # Try to find user (silent fail for security)
        user = None
        try:
            if '@' in identifier:
                user = User.objects.get(email__iexact=identifier, is_active=True)
            else:
                user = User.objects.get(username=identifier, is_active=True)
        except User.DoesNotExist:
            pass

        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            self.send_password_reset_email(user, uid, token)
            # Store current time in cache (expires after cooldown_seconds)
            cache.set(cache_key, timezone.now(), timeout=cooldown_seconds)

        # Always return the same success message (no user enumeration)
        return Response({'message': 'لینک بازیابی رمز عبور به ایمیل شما ارسال شد'})


    def send_password_reset_email(self, user, uid, token):
        """Send password reset email in Persian"""
        try:
            reset_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/reset-password/{uid}/{token}/"
            
            subject = 'بازیابی رمز عبور - داروخانه دکتر نقی پور'
            message = f"""
            {user.first_name or user.username} عزیز،

            درخواست بازیابی رمز عبور برای حساب کاربری شما ثبت شده است.

            نام کاربری: {user.username}

            برای تنظیم رمز عبور جدید، روی لینک زیر کلیک کنید:
            {reset_url}

            این لینک تا ۲۴ ساعت معتبر است.

            اگر درخواستی برای بازیابی رمز عبور ندادید، لطفاً این ایمیل را نادیده بگیرید.

            با احترام،
            تیم داروخانه دکتر نقی پور
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send password reset email: {e}")

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def password_reset_confirm(self, request):
        """Confirm password reset"""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, serializer.validated_data['token']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                
                # Clear existing tokens
                Token.objects.filter(user=user).delete()
                
                return Response({
                    'message': 'Password reset successfully'
                })
            else:
                return Response({
                    'error': 'Invalid or expired token'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Invalid reset link'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def deactivate_account(self, request):
        """Deactivate user account"""
        user = request.user
        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save()
        
        # Clear auth tokens
        Token.objects.filter(user=user).delete()
        
        return Response({
            'message': 'Account deactivated successfully'
        })

    # ========== SMS OTP LOGIN ==========
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def request_otp(self, request):
        """Request OTP code via SMS"""
        phone = request.data.get('phone_number')
        if not phone:
            return Response(
                {'error': 'شماره موبایل الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            send_verification_code(phone)
            return Response(
                {'message': 'کد تایید به شماره شما ارسال شد'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_otp(self, request):
        """Verify OTP and login/register user"""
        phone = request.data.get('phone_number')
        code = request.data.get('code')
        if not phone or not code:
            return Response(
                {'error': 'شماره موبایل و کد تایید الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            otp = OTP.objects.get(phone_number=phone)
        except ObjectDoesNotExist:
            return Response(
                {'error': 'درخواست کد تایید یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not otp.is_valid():
            return Response(
                {'error': 'کد تایید منقضی شده یا قبلاً استفاده شده است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp.code != code:
            otp.attempt_count += 1
            otp.save(update_fields=['attempt_count'])
            remaining = 5 - otp.attempt_count
            if remaining <= 0:
                otp.delete()
                return Response(
                    {'error': 'تعداد تلاش نامعتبر بیش از حد مجاز. لطفاً دوباره درخواست کد دهید.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'error': f'کد نامعتبر. {remaining} تلاش باقی مانده.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark OTP as verified
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        # Find existing user by phone number, or create new
        user = User.objects.filter(phone_number=phone).first()
        if not user:
            user = User.objects.create_user(
                username=phone,
                email='',
                phone_number=phone,
                first_name='',
                last_name='',
                user_type='customer',
                is_active=True
            )
        else:
            # Ensure phone_number is set (should be, but for safety)
            if not user.phone_number:
                user.phone_number = phone
                user.save(update_fields=['phone_number'])

        # Generate JWT tokens (simplejwt)
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def set_password_with_otp(self, request):
        """
        Change or set password after OTP verification (no authentication required).
        Requires: phone_number, code, new_password, confirm_password
        """
        phone = request.data.get('phone_number')
        code = request.data.get('code')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([phone, code, new_password, confirm_password]):
            return Response(
                {'error': 'همه فیلدها الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'رمز عبور و تکرار آن مطابقت ندارند'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify OTP
        try:
            otp = OTP.objects.get(phone_number=phone)
        except OTP.DoesNotExist:
            return Response(
                {'error': 'درخواست کد تایید یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not otp.is_valid():
            return Response(
                {'error': 'کد تایید منقضی شده یا قبلاً استفاده شده است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp.code != code:
            otp.attempt_count += 1
            otp.save(update_fields=['attempt_count'])
            remaining = 5 - otp.attempt_count
            if remaining <= 0:
                otp.delete()
                return Response(
                    {'error': 'تعداد تلاش نامعتبر بیش از حد مجاز. لطفاً دوباره درخواست کد دهید.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'error': f'کد نامعتبر. {remaining} تلاش باقی مانده.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark OTP as used
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        # Find user by phone number (not from request.user)
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response(
                {'error': 'کاربری با این شماره موبایل یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        # Invalidate existing auth tokens (optional)
        Token.objects.filter(user=user).delete()

        return Response({'message': 'رمز عبور با موفقیت تغییر کرد'})


# Custom Serializer for Username Authentication
class CustomAuthTokenSerializer(auth_serializers.AuthTokenSerializer):
    """Custom auth token serializer that accepts username instead of email"""
    username = auth_serializers.serializers.CharField(label="Username", write_only=True)
    password = auth_serializers.serializers.CharField(
        label="Password",
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )
    token = auth_serializers.serializers.CharField(label="Token", read_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                              username=username, password=password)

            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise auth_serializers.serializers.ValidationError(msg, code='authorization')
            
            if not user.is_active:
                msg = 'User account is disabled.'
                raise auth_serializers.serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "username" and "password".'
            raise auth_serializers.serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class CustomAuthToken(ObtainAuthToken):
    """Custom authentication view that accepts username and returns user data along with token"""
    serializer_class = CustomAuthTokenSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                         context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': f'Welcome back, {user.first_name or user.username}!'
        })


class LogoutView(APIView):
    """Logout view that deletes the auth token"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the user's token
            Token.objects.filter(user=request.user).delete()
            return Response({
                'message': 'Successfully logged out'
            })
        except Exception as e:
            return Response({
                'error': 'Error logging out'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user profiles"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current user's profile"""
        try:
            profile = UserProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({
                'message': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def upload_avatar(self, request):
        """Upload user avatar"""
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            if 'avatar' not in request.FILES:
                return Response({
                    'error': 'No avatar file provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            profile.avatar = request.FILES['avatar']
            profile.save()
            
            return Response({
                'message': 'Avatar uploaded successfully',
                'avatar_url': profile.avatar.url if profile.avatar else None
            })
        except Exception as e:
            return Response({
                'error': f'Failed to upload avatar: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserAddressViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user addresses"""
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return UserAddress.objects.all()
        return UserAddress.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set address as default"""
        address = self.get_object()
        
        # Remove default from other addresses
        UserAddress.objects.filter(
            user=address.user,
            address_type=address.address_type
        ).update(is_default=False)
        
        # Set this address as default
        address.is_default = True
        address.save()
        
        return Response({
            'message': 'Address set as default'
        })
    
    @action(detail=False, methods=['get'])
    def default_shipping(self, request):
        """Get default shipping address"""
        try:
            address = UserAddress.objects.get(
                user=request.user,
                address_type='shipping',
                is_default=True
            )
            serializer = self.get_serializer(address)
            return Response(serializer.data)
        except UserAddress.DoesNotExist:
            return Response({
                'message': 'No default shipping address found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def default_billing(self, request):
        """Get default billing address"""
        try:
            address = UserAddress.objects.get(
                user=request.user,
                address_type='billing',
                is_default=True
            )
            serializer = self.get_serializer(address)
            return Response(serializer.data)
        except UserAddress.DoesNotExist:
            return Response({
                'message': 'No default billing address found'
            }, status=status.HTTP_404_NOT_FOUND)


class PharmacyLicenseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pharmacy licenses"""
    serializer_class = PharmacyLicenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return PharmacyLicense.objects.all()
        return PharmacyLicense.objects.filter(user=self.request.user)
    
    def get_permissions(self):
        """Admin can view all, users can only view their own"""
        if self.action in ['list', 'retrieve'] and self.request.user.is_staff:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Approve pharmacy license"""
        license = self.get_object()
        license.status = 'approved'
        license.approved_by = request.user
        license.approved_at = timezone.now()
        license.save()
        
        # Send approval email
        self.send_approval_email(license)
        
        return Response({
            'message': 'License approved successfully'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Reject pharmacy license"""
        license = self.get_object()
        license.status = 'rejected'
        license.rejection_reason = request.data.get('reason', '')
        license.save()
        
        # Send rejection email
        self.send_rejection_email(license)
        
        return Response({
            'message': 'License rejected'
        })
    
    def send_approval_email(self, license):
        """Send license approval email"""
        try:
            subject = 'Pharmacy License Approved - Pharma API'
            message = f"""
            Dear {license.user.first_name or license.user.username},
            
            Congratulations! Your pharmacy license has been approved.
            
            License Details:
            - License Number: {license.license_number}
            - Pharmacy Name: {license.pharmacy_name}
            - Status: Approved
            
            You can now access all pharmaceutical products and services.
            
            Best regards,
            Pharma API Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [license.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send approval email: {e}")
    
    def send_rejection_email(self, license):
        """Send license rejection email"""
        try:
            subject = 'Pharmacy License Update - Pharma API'
            message = f"""
            Dear {license.user.first_name or license.user.username},
            
            We regret to inform you that your pharmacy license application has been rejected.
            
            License Details:
            - License Number: {license.license_number}
            - Pharmacy Name: {license.pharmacy_name}
            - Status: Rejected
            
            Reason: {license.rejection_reason}
            
            Please review the requirements and submit a new application if needed.
            
            Best regards,
            Pharma API Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [license.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send rejection email: {e}")
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get pending license approvals (admin only)"""
        if not request.user.is_staff:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        pending_licenses = PharmacyLicense.objects.filter(status='pending')
        serializer = self.get_serializer(pending_licenses, many=True)
        return Response(serializer.data)


# Additional views for easier frontend integration
class LoginView(APIView):
    """Simple login view for frontend"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # برای دیباگ
        print(f"Login request data: {request.data}")
        
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': f'Welcome back, {user.first_name or user.username}!'
            }, status=status.HTTP_200_OK)
        
        # برای دیباگ
        print(f"Login validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    """Simple registration view for frontend"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Account created successfully'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Add user data to the response
        user_serializer = UserSerializer(self.user)
        data['user'] = user_serializer.data
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer