from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from homes.models import FloorPlan, Home
from locations.models import LocationNode
from .models import Item, ItemLocationHistory


class ItemApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)
        self.home = Home.objects.create(owner=self.user, name="My Home")
        self.floor_plan = FloorPlan.objects.create(home=self.home, name="1F")
        self.room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="LIVING",
            name="Living Room",
        )
        self.zone_a = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=self.room,
            node_type=LocationNode.NodeType.ZONE,
            code="A",
            name="Zone A",
        )
        self.zone_b = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=self.room,
            node_type=LocationNode.NodeType.ZONE,
            code="B",
            name="Zone B",
        )
        self.item = Item.objects.create(
            owner=self.user,
            name="Passport",
            current_location_node=self.zone_a,
        )

    def test_searches_by_location_code(self):
        url = reverse("item-list")
        response = self.client.get(url, {"location_code": "LIVING-A"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Passport")

    def test_moves_item_and_creates_history(self):
        url = reverse("item-move", args=[self.item.id])
        response = self.client.post(
            url,
            {"to_location_node": self.zone_b.id, "memo": "Moved for testing"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_location_node, self.zone_b)
        self.assertEqual(ItemLocationHistory.objects.count(), 1)
        self.assertEqual(
            ItemLocationHistory.objects.first().from_location_node,
            self.zone_a,
        )
