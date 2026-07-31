from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class RegisterTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("auth-register")

    def test_creates_user_with_generated_username(self):
        response = self.client.post(
            self.url,
            {"email": "someone@example.com", "password": "Str0ng-Passphrase"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "someone")
        self.assertNotIn("password", response.data)

    def test_rejects_a_password_the_reset_flow_would_also_reject(self):
        """Registration used to only enforce min_length, so a password that
        AUTH_PASSWORD_VALIDATORS rejects could still be used to sign up."""
        response = self.client.post(
            self.url,
            {"email": "someone@example.com", "password": "12345678"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(email="someone@example.com").exists())

    def test_rejects_password_similar_to_email(self):
        response = self.client.post(
            self.url,
            {"email": "jonathan@example.com", "password": "jonathan@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("auth-login")
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="Str0ng-Passphrase",
        )

    def test_logs_in_with_email_or_username(self):
        for identifier in ("tester", "TESTER@example.com"):
            with self.subTest(identifier=identifier):
                response = self.client.post(
                    self.url,
                    {"identifier": identifier, "password": "Str0ng-Passphrase"},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.client.post(reverse("auth-logout"))

    def test_throttles_repeated_failed_logins(self):
        # DRF binds DEFAULT_THROTTLE_RATES to the throttle class at import time,
        # so override_settings cannot change it here. Drive the real configured
        # rate instead, which also asserts the setting is actually wired up.
        allowed = int(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"].split("/")[0],
        )

        for _ in range(allowed):
            response = self.client.post(
                self.url,
                {"identifier": "tester", "password": "wrong"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            self.url,
            {"identifier": "tester", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # A throttled attacker must not be able to get in with the real password.
        response = self.client.post(
            self.url,
            {"identifier": "tester", "password": "Str0ng-Passphrase"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class OwnershipIsolationTests(APITestCase):
    """The serializers carry a lot of cross-user validation but had no tests."""

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="Str0ng-Passphrase",
        )
        self.intruder = User.objects.create_user(
            username="intruder",
            email="intruder@example.com",
            password="Str0ng-Passphrase",
        )

        from homes.models import FloorPlan, Home
        from items.models import Category, Item
        from locations.models import LocationNode

        self.home = Home.objects.create(owner=self.owner, name="Owner Home")
        self.floor_plan = FloorPlan.objects.create(home=self.home, name="1F")
        self.node = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="R1",
            name="Living Room",
        )
        self.category = Category.objects.create(owner=self.owner, name="Docs")
        self.item = Item.objects.create(owner=self.owner, name="Passport")

        self.client.force_authenticate(self.intruder)

    def test_other_users_records_are_not_listed(self):
        for route in ("home-list", "floor-plan-list", "location-node-list", "item-list"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["results"], [])

    def test_other_users_records_are_not_retrievable(self):
        cases = (
            ("home-detail", self.home.id),
            ("floor-plan-detail", self.floor_plan.id),
            ("location-node-detail", self.node.id),
            ("item-detail", self.item.id),
        )
        for route, pk in cases:
            with self.subTest(route=route):
                response = self.client.get(reverse(route, args=[pk]))
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_attach_an_item_to_another_users_location(self):
        response = self.client.post(
            reverse("item-list"),
            {"name": "Stolen", "current_location_node": self.node.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_attach_an_item_to_another_users_category(self):
        response = self.client.post(
            reverse("item-list"),
            {"name": "Stolen", "category": self.category.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_a_floor_plan_in_another_users_home(self):
        response = self.client.post(
            reverse("floor-plan-list"),
            {"home": self.home.id, "name": "Sneaky"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_a_location_node_under_another_users_parent(self):
        response = self.client.post(
            reverse("location-node-list"),
            {"parent": self.node.id, "node_type": "FURNITURE", "code": "F1", "name": "Shelf"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
