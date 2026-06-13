from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from homes.models import FloorPlan, Home
from .models import LocationNode


class LocationNodeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password123",
        )
        self.home = Home.objects.create(owner=self.user, name="My Home")
        self.floor_plan = FloorPlan.objects.create(home=self.home, name="1F")

    def test_generates_full_code_and_path(self):
        room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="LIVING",
            name="Living Room",
        )
        zone = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=room,
            node_type=LocationNode.NodeType.ZONE,
            code="A",
            name="Zone A",
        )
        compartment = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=zone,
            node_type=LocationNode.NodeType.COMPARTMENT,
            code="1",
            name="First Drawer",
        )

        self.assertEqual(compartment.full_code, "LIVING-A-1")
        self.assertEqual(compartment.path, "Living Room / Zone A / First Drawer")
        self.assertEqual(compartment.level, 2)

    def test_rejects_duplicate_code_under_same_parent(self):
        room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="LIVING",
            name="Living Room",
        )
        LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=room,
            node_type=LocationNode.NodeType.ZONE,
            code="A",
            name="Zone A",
        )

        with self.assertRaises(ValidationError):
            LocationNode.objects.create(
                home=self.home,
                floor_plan=self.floor_plan,
                parent=room,
                node_type=LocationNode.NodeType.ZONE,
                code="A",
                name="Another Zone A",
            )
