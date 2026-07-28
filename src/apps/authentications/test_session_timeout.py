from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework_simplejwt.exceptions import InvalidToken
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from apps.authentications.service.authentication import CustomJWTAuthentication

User = get_user_model()

class CustomJWTAuthenticationTimeoutTest(TestCase):
    def setUp(self):
        # Create a test user with a password and required fields
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="TestPassword123!",
            first_name="Test",
            last_name="User",
            role="tashkilot_rahbari"
        )
        self.auth = CustomJWTAuthentication()
        self.token = AccessToken.for_user(self.user)

    def test_new_user_login_sets_last_activity_and_authenticates(self):
        # Initially, last_activity is not set (or we can set it to None)
        self.user.last_activity = None
        self.user.save()
        
        # Authenticate
        returned_user = self.auth.get_user(self.token)
        self.assertEqual(returned_user, self.user)
        self.assertIsNotNone(returned_user.last_activity)

    def test_active_user_within_timeout_authenticates(self):
        # Set last_activity to 5 minutes ago (timeout is 15 minutes)
        now = timezone.now()
        self.user.last_activity = now - timedelta(minutes=5)
        self.user.save()

        returned_user = self.auth.get_user(self.token)
        self.assertEqual(returned_user, self.user)

    def test_inactive_user_beyond_timeout_raises_invalid_token(self):
        # Set last_activity to 16 minutes ago (timeout is 15 minutes)
        now = timezone.now()
        self.user.last_activity = now - timedelta(minutes=16)
        self.user.save()

        with self.assertRaises(InvalidToken):
            self.auth.get_user(self.token)

    def test_touch_interval_updates_last_activity(self):
        # Set last_activity to 70 seconds ago (touch interval is 60 seconds)
        now = timezone.now()
        seventy_seconds_ago = now - timedelta(seconds=70)
        self.user.last_activity = seventy_seconds_ago
        self.user.save()

        returned_user = self.auth.get_user(self.token)
        self.assertEqual(returned_user, self.user)
        
        # last_activity must be updated to around now (greater than seventy_seconds_ago)
        self.user.refresh_from_db()
        self.assertGreater(self.user.last_activity, seventy_seconds_ago)

    def test_touch_interval_ignores_frequent_requests(self):
        # Set last_activity to 30 seconds ago (touch interval is 60 seconds, so it shouldn't update)
        now = timezone.now()
        thirty_seconds_ago = now - timedelta(seconds=30)
        self.user.last_activity = thirty_seconds_ago
        self.user.save()

        returned_user = self.auth.get_user(self.token)
        self.assertEqual(returned_user, self.user)
        
        self.user.refresh_from_db()
        # last_activity should NOT be updated, it should remain thirty_seconds_ago (within precision limits)
        self.assertAlmostEqual(
            self.user.last_activity.replace(microsecond=0),
            thirty_seconds_ago.replace(microsecond=0),
            delta=timedelta(seconds=1)
        )

