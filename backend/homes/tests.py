from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import FloorPlan, Home


class HomeApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="Str0ng-Passphrase",
        )
        self.client.force_authenticate(self.user)

    def test_creates_home_owned_by_the_caller(self):
        response = self.client.post(reverse("home-list"), {"name": "My Home"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["owner"], self.user.id)

    def test_rejects_duplicate_home_name_for_the_same_owner(self):
        Home.objects.create(owner=self.user, name="My Home")

        response = self.client.post(reverse("home-list"), {"name": "My Home"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_allows_the_same_home_name_for_a_different_owner(self):
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="Str0ng-Passphrase",
        )
        Home.objects.create(owner=other, name="My Home")

        response = self.client.post(reverse("home-list"), {"name": "My Home"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_rejects_duplicate_floor_plan_name_within_a_home(self):
        home = Home.objects.create(owner=self.user, name="My Home")
        FloorPlan.objects.create(home=home, name="1F")

        response = self.client.post(
            reverse("floor-plan-list"),
            {"home": home.id, "name": "1F"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleting_a_home_removes_its_floor_plans(self):
        home = Home.objects.create(owner=self.user, name="My Home")
        FloorPlan.objects.create(home=home, name="1F")

        response = self.client.delete(reverse("home-detail", args=[home.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FloorPlan.objects.count(), 0)
