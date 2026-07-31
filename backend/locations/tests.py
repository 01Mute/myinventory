from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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

    def test_renaming_a_node_resyncs_descendant_paths(self):
        room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="LIVING",
            name="Living Room",
        )
        furniture = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=room,
            node_type=LocationNode.NodeType.FURNITURE,
            code="F1",
            name="Shelf",
        )
        compartment = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=furniture,
            node_type=LocationNode.NodeType.COMPARTMENT,
            code="C1",
            name="Top",
        )

        room.name = "Study"
        room.code = "STUDY"
        room.save()

        furniture.refresh_from_db()
        compartment.refresh_from_db()
        self.assertEqual(furniture.full_code, "STUDY-F1")
        self.assertEqual(furniture.path, "Study / Shelf")
        self.assertEqual(compartment.full_code, "STUDY-F1-C1")
        self.assertEqual(compartment.path, "Study / Shelf / Top")

    def test_reparenting_a_node_resyncs_descendant_codes_and_levels(self):
        first_room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="R1",
            name="Room One",
        )
        second_room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="R2",
            name="Room Two",
        )
        furniture = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.FURNITURE,
            code="F1",
            name="Shelf",
        )
        compartment = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=furniture,
            node_type=LocationNode.NodeType.COMPARTMENT,
            code="C1",
            name="Top",
        )

        furniture.parent = first_room
        furniture.save()
        compartment.refresh_from_db()
        self.assertEqual(compartment.full_code, "R1-F1-C1")
        self.assertEqual(compartment.level, 2)

        furniture.parent = second_room
        furniture.save()
        compartment.refresh_from_db()
        self.assertEqual(compartment.full_code, "R2-F1-C1")
        self.assertEqual(compartment.path, "Room Two / Shelf / Top")
        self.assertEqual(compartment.level, 2)

        furniture.parent = None
        furniture.save()
        compartment.refresh_from_db()
        self.assertEqual(compartment.full_code, "F1-C1")
        self.assertEqual(compartment.path, "Shelf / Top")
        self.assertEqual(compartment.level, 1)

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

    def test_database_rejects_duplicate_codes_even_with_null_columns(self):
        """A single constraint over nullable floor_plan/parent is not enforced
        by Postgres, so the DB accepted duplicates that raced past clean()."""
        null_combinations = (
            {"floor_plan": self.floor_plan, "parent": None},
            {"floor_plan": None, "parent": None},
        )

        for index, combination in enumerate(null_combinations):
            code = f"DUP{index}"
            with self.subTest(**combination):
                LocationNode.objects.create(
                    home=self.home,
                    node_type=LocationNode.NodeType.ROOM,
                    code=code,
                    name=f"First {code}",
                    **combination,
                )
                duplicate = LocationNode(
                    home=self.home,
                    node_type=LocationNode.NodeType.ROOM,
                    code=code,
                    name=f"Second {code}",
                    **combination,
                )
                duplicate._set_hierarchy_fields()

                # Bypass full_clean() to prove the constraint itself holds.
                with self.assertRaises(IntegrityError), transaction.atomic():
                    super(LocationNode, duplicate).save()


class LocationTreeEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="Str0ng-Passphrase",
        )
        self.client.force_authenticate(self.user)
        self.home = Home.objects.create(owner=self.user, name="My Home")
        self.floor_plan = FloorPlan.objects.create(home=self.home, name="1F")

        self.room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="R1",
            name="Living Room",
        )
        self.furniture = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=self.room,
            node_type=LocationNode.NodeType.FURNITURE,
            code="F1",
            name="Shelf",
        )
        for index in range(3):
            LocationNode.objects.create(
                home=self.home,
                floor_plan=self.floor_plan,
                parent=self.furniture,
                node_type=LocationNode.NodeType.COMPARTMENT,
                code=f"C{index + 1}",
                name=f"Shelf {index + 1}",
            )

    def test_returns_the_full_nested_subtree(self):
        response = self.client.get(reverse("location-node-tree", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_code"], "R1")

        furniture = response.data["children"][0]
        self.assertEqual(furniture["full_code"], "R1-F1")
        self.assertEqual(
            [row["full_code"] for row in furniture["children"]],
            ["R1-F1-C1", "R1-F1-C2", "R1-F1-C3"],
        )

    def test_subtree_loads_in_a_constant_number_of_queries(self):
        """The old serializer recursed with one query per node, so the tree got
        slower the more locations a user had."""
        url = reverse("location-node-tree", args=[self.room.id])
        with CaptureQueriesContext(connection) as baseline:
            self.client.get(url)

        # Adding descendants, including a deeper level, must not add queries.
        deeper = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=self.furniture,
            node_type=LocationNode.NodeType.COMPARTMENT,
            code="C4",
            name="Shelf 4",
        )
        for index in range(3):
            LocationNode.objects.create(
                home=self.home,
                floor_plan=self.floor_plan,
                parent=deeper,
                node_type=LocationNode.NodeType.BOX,
                code=f"B{index + 1}",
                name=f"Box {index + 1}",
            )

        with CaptureQueriesContext(connection) as after:
            response = self.client.get(url)

        self.assertEqual(len(after), len(baseline))
        self.assertEqual(
            [row["full_code"] for row in response.data["children"][0]["children"]],
            ["R1-F1-C1", "R1-F1-C2", "R1-F1-C3", "R1-F1-C4"],
        )
