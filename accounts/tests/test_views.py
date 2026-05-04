# accounts/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import UserProfile, Address, UserPreference, UserDocument

User = get_user_model()

class UserViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123',
            first_name='Test',
            last_name='User'
        )
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_user_list_forbidden(self):
        """Test that regular users cannot list all users"""
        url = reverse('accounts:user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_list_admin(self):
        """Test that admins can list all users"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('accounts:user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 2)  # At least our 2 test users

    def test_get_user_detail(self):
        """Test getting user details"""
        url = reverse('accounts:user-detail', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)

    def test_get_other_user_detail_forbidden(self):
        """Test that users cannot access other users' details"""
        url = reverse('accounts:user-detail', args=[self.admin_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_user(self):
        """Test updating user details"""
        url = reverse('accounts:user-detail', args=[self.user.id])
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, data['first_name'])
        self.assertEqual(self.user.last_name, data['last_name'])


class RegistrationViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('accounts:register')
        self.user_data = {
            'email': 'newuser@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'first_name': 'New',
            'last_name': 'User'
        }

    def test_register_user_success(self):
        """Test registering a new user is successful"""
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.user_data['email']).exists())

    def test_register_user_password_mismatch(self):
        """Test registration fails when passwords don't match"""
        self.user_data['password_confirm'] = 'differentpassword'
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_register_user_email_exists(self):
        """Test registration fails when email already exists"""
        # Create user with the email first
        User.objects.create_user(email=self.user_data['email'], password='somepassword')
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class AddressViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.client.force_authenticate(user=self.user)
        self.address_data = {
            'address_type': 'shipping',
            'address_line1': '123 Test St',
            'city': 'Test City',
            'state': 'Test State',
            'postal_code': '12345',
            'country': 'Test Country',
            'is_default': True
        }
        self.address = Address.objects.create(user=self.user, **self.address_data)
        self.list_url = reverse('accounts:address-list')
        self.detail_url = reverse('accounts:address-detail', args=[self.address.id])

    def test_get_address_list(self):
        """Test getting list of user's addresses"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['address_line1'], self.address_data['address_line1'])

    def test_create_address(self):
        """Test creating a new address"""
        new_address_data = {
            'address_type': 'billing',
            'address_line1': '456 Other St',
            'city': 'Other City',
            'state': 'Other State',
            'postal_code': '67890',
            'country': 'Other Country',
            'is_default': True
        }
        response = self.client.post(self.list_url, new_address_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.count(), 2)
        self.assertTrue(Address.objects.filter(address_line1=new_address_data['address_line1']).exists())

    def test_update_address(self):
        """Test updating an address"""
        update_data = {'address_line1': '789 Updated St'}
        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.address.refresh_from_db()
        self.assertEqual(self.address.address_line1, update_data['address_line1'])

    def test_delete_address(self):
        """Test deleting an address"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Address.objects.filter(id=self.address.id).exists())


class ProfileViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.client.force_authenticate(user=self.user)
        self.profile = UserProfile.objects.get(user=self.user)  # Auto-created
        self.url = reverse('accounts:profile')

    def test_get_profile(self):
        """Test getting user profile"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], self.user.id)

    def test_update_profile(self):
        """Test updating user profile"""
        update_data = {
            'phone_number': '+1234567890',
            'bio': 'Updated bio'
        }
        response = self.client.patch(self.url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone_number, update_data['phone_number'])
        self.assertEqual(self.profile.bio, update_data['bio'])


class PasswordChangeViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='oldpassword123'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('accounts:password-change')
        self.password_data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword456',
            'new_password_confirm': 'newpassword456'
        }

    def test_change_password_success(self):
        """Test changing password successfully"""
        response = self.client.post(self.url, self.password_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password_data['new_password']))

    def test_change_password_wrong_old_password(self):
        """Test changing password with wrong old password"""
        self.password_data['old_password'] = 'wrongpassword'
        response = self.client.post(self.url, self.password_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(self.password_data['new_password']))

    def test_change_password_mismatch(self):
        """Test changing password with mismatched new passwords"""
        self.password_data['new_password_confirm'] = 'differentpassword'
        response = self.client.post(self.url, self.password_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password_confirm', response.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(self.password_data['new_password']))