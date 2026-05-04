# accounts/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from accounts.models import UserProfile, Address, UserPreference, UserDocument

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'password': 'securepassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_create_user(self):
        """Test creating a user with email is successful"""
        self.assertEqual(self.user.email, self.user_data['email'])
        self.assertEqual(self.user.first_name, self.user_data['first_name'])
        self.assertEqual(self.user.last_name, self.user_data['last_name'])
        self.assertTrue(self.user.check_password(self.user_data['password']))
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_active)

    def test_create_superuser(self):
        """Test creating a superuser"""
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_email_normalized(self):
        """Test email is normalized when creating user"""
        email = 'test@EXAMPLE.COM'
        user = User.objects.create_user(email=email, password='test123')
        self.assertEqual(user.email, email.lower())

    def test_email_required(self):
        """Test that creating user without email raises error"""
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='test123')

    def test_user_str(self):
        """Test the string representation of user"""
        self.assertEqual(str(self.user), f"{self.user.first_name} {self.user.last_name}")


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123',
            first_name='Test',
            last_name='User'
        )
        self.profile = UserProfile.objects.get(user=self.user)  # Auto-created via signal

    def test_profile_created_automatically(self):
        """Test profile is created automatically when user is created"""
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.user, self.user)

    def test_profile_str(self):
        """Test the string representation of profile"""
        self.assertEqual(str(self.profile), f"Profile for {self.user.email}")


class AddressModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.address_data = {
            'user': self.user,
            'address_type': 'shipping',
            'address_line1': '123 Test St',
            'city': 'Test City',
            'state': 'Test State',
            'postal_code': '12345',
            'country': 'Test Country',
            'is_default': True
        }
        self.address = Address.objects.create(**self.address_data)

    def test_create_address(self):
        """Test creating an address"""
        self.assertEqual(self.address.user, self.user)
        self.assertEqual(self.address.address_line1, self.address_data['address_line1'])
        self.assertEqual(self.address.city, self.address_data['city'])
        self.assertEqual(self.address.is_default, self.address_data['is_default'])

    def test_address_str(self):
        """Test the string representation of address"""
        expected_str = f"{self.address_data['address_type']} address for {self.user.email}"
        self.assertEqual(str(self.address), expected_str)

    def test_default_address_uniqueness(self):
        """Test that only one default address per type per user is allowed"""
        # Create another default address of the same type
        with self.assertRaises(ValidationError):
            address2 = Address(
                user=self.user,
                address_type='shipping',
                address_line1='456 Other St',
                city='Other City',
                state='Other State',
                postal_code='67890',
                country='Other Country',
                is_default=True
            )
            address2.full_clean()  # This should raise ValidationError


class UserPreferenceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.preferences = UserPreference.objects.create(
            user=self.user,
            language='en',
            timezone='UTC',
            currency='USD',
            email_notifications=True
        )

    def test_create_preferences(self):
        """Test creating user preferences"""
        self.assertEqual(self.preferences.user, self.user)
        self.assertEqual(self.preferences.language, 'en')
        self.assertEqual(self.preferences.timezone, 'UTC')
        self.assertEqual(self.preferences.currency, 'USD')
        self.assertTrue(self.preferences.email_notifications)

    def test_preferences_str(self):
        """Test the string representation of preferences"""
        self.assertEqual(str(self.preferences), f"Preferences for {self.user.email}")


class UserDocumentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.document = UserDocument.objects.create(
            user=self.user,
            document_type='id_proof',
            document_number='ABC123456',
            document_status='pending'
        )

    def test_create_document(self):
        """Test creating a user document"""
        self.assertEqual(self.document.user, self.user)
        self.assertEqual(self.document.document_type, 'id_proof')
        self.assertEqual(self.document.document_number, 'ABC123456')
        self.assertEqual(self.document.document_status, 'pending')

    def test_document_str(self):
        """Test the string representation of document"""
        expected_str = f"{self.document.document_type} for {self.user.email}"
        self.assertEqual(str(self.document), expected_str)