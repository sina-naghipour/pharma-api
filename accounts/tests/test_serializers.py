# accounts/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from accounts.serializers import (
    UserSerializer, UserProfileSerializer, AddressSerializer, 
    UserPreferenceSerializer, UserDocumentSerializer,
    UserRegistrationSerializer, PasswordChangeSerializer
)
from accounts.models import UserProfile, Address, UserPreference, UserDocument

User = get_user_model()

class UserSerializerTest(TestCase):
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'password': 'securepassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.serializer = UserSerializer(instance=self.user)

    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'email', 'first_name', 'last_name', 'date_joined', 'is_active']
        )

    def test_email_field_content(self):
        """Test email field content"""
        data = self.serializer.data
        self.assertEqual(data['email'], self.user_data['email'])


class UserRegistrationSerializerTest(TestCase):
    def setUp(self):
        self.user_data = {
            'email': 'newuser@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'first_name': 'New',
            'last_name': 'User'
        }
        self.serializer = UserRegistrationSerializer(data=self.user_data)

    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())

    def test_password_mismatch(self):
        """Test password mismatch validation"""
        self.user_data['password_confirm'] = 'differentpassword'
        serializer = UserRegistrationSerializer(data=self.user_data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_create_user(self):
        """Test creating a user with the serializer"""
        self.assertTrue(self.serializer.is_valid())
        user = self.serializer.save()
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.first_name, self.user_data['first_name'])
        self.assertEqual(user.last_name, self.user_data['last_name'])
        self.assertTrue(user.check_password(self.user_data['password']))


class UserProfileSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile_data = {
            'phone_number': '+1234567890',
            'date_of_birth': '1990-01-01',
            'bio': 'Test bio'
        }
        # Update profile with test data
        for key, value in self.profile_data.items():
            setattr(self.profile, key, value)
        self.profile.save()
        self.serializer = UserProfileSerializer(instance=self.profile)

    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'user', 'phone_number', 'date_of_birth', 'bio', 'profile_picture']
        )

    def test_field_content(self):
        """Test field content"""
        data = self.serializer.data
        self.assertEqual(data['phone_number'], self.profile_data['phone_number'])
        self.assertEqual(data['bio'], self.profile_data['bio'])
        self.assertEqual(data['date_of_birth'], self.profile_data['date_of_birth'])


class AddressSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.address_data = {
            'user': self.user.id,
            'address_type': 'shipping',
            'address_line1': '123 Test St',
            'city': 'Test City',
            'state': 'Test State',
            'postal_code': '12345',
            'country': 'Test Country',
            'is_default': True
        }
        self.serializer = AddressSerializer(data=self.address_data)

    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())

    def test_create_address(self):
        """Test creating an address with the serializer"""
        self.assertTrue(self.serializer.is_valid())
        address = self.serializer.save()
        self.assertEqual(address.user, self.user)
        self.assertEqual(address.address_line1, self.address_data['address_line1'])
        self.assertEqual(address.city, self.address_data['city'])
        self.assertTrue(address.is_default)


class PasswordChangeSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='oldpassword123'
        )
        self.password_data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword456',
            'new_password_confirm': 'newpassword456'
        }
        self.serializer = PasswordChangeSerializer(
            data=self.password_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )

    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())

    def test_incorrect_old_password(self):
        """Test incorrect old password validation"""
        self.password_data['old_password'] = 'wrongpassword'
        serializer = PasswordChangeSerializer(
            data=self.password_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('old_password', serializer.errors)

    def test_password_mismatch(self):
        """Test password mismatch validation"""
        self.password_data['new_password_confirm'] = 'differentpassword'
        serializer = PasswordChangeSerializer(
            data=self.password_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('new_password_confirm', serializer.errors)

    def test_save_changes_password(self):
        """Test saving serializer changes the password"""
        self.assertTrue(self.serializer.is_valid())
        self.serializer.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password_data['new_password']))