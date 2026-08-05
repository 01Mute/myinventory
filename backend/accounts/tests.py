import json
import shutil
import tempfile
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from homes.models import FloorPlan, Home
from items.models import Category, Item, ItemLocationHistory, Tag
from locations.models import LocationNode

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


class BackupDemoTests(TestCase):
    """The demo account is the one strangers can log into and edit, so a
    snapshot of it has to be both takeable and restorable."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

        self.user = User.objects.create_user(
            username="test",
            email="test@example.com",
            password="password123",
        )
        self.home = Home.objects.create(owner=self.user, name="My Home")
        self.floor_plan = FloorPlan.objects.create(home=self.home, name="1F")
        self.room = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            node_type=LocationNode.NodeType.ROOM,
            code="LIVING",
            name="Living Room",
        )
        self.shelf = LocationNode.objects.create(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=self.room,
            node_type=LocationNode.NodeType.BOX,
            code="A",
            name="Shelf A",
        )
        self.category = Category.objects.create(owner=self.user, name="Tools")
        self.tag = Tag.objects.create(owner=self.user, name="spare")
        self.item = Item.objects.create(
            owner=self.user,
            name="Passport",
            category=self.category,
            current_location_node=self.shelf,
        )
        self.item.tags.add(self.tag)
        ItemLocationHistory.objects.create(
            item=self.item,
            from_location_node=self.room,
            to_location_node=self.shelf,
            created_by=self.user,
        )

    def backup(self, **kwargs):
        call_command("backup_demo", out=str(self.root), stdout=StringIO(), **kwargs)
        return sorted(self.root.glob("demo-*"))[-1]

    def test_writes_a_snapshot_of_the_account(self):
        directory = self.backup()
        objects = json.loads((directory / "data.json").read_text(encoding="utf-8"))

        models = [row["model"] for row in objects]
        self.assertIn("items.item", models)
        self.assertIn("items.itemlocationhistory", models)
        self.assertIn("locations.locationnode", models)

    def test_stores_ownership_as_the_fixture_placeholder(self):
        """Backups have to be loadable by seed_demo, which swaps a placeholder
        owner for whichever user row it just created. A real user id baked into
        the file would restore onto an account that may not exist."""
        directory = self.backup()
        objects = json.loads((directory / "data.json").read_text(encoding="utf-8"))

        owners = {
            row["fields"]["owner"] for row in objects if "owner" in row["fields"]
        }
        self.assertEqual(owners, {2})
        self.assertNotIn(self.user.pk, owners)

    def test_leaves_other_accounts_out(self):
        stranger = User.objects.create_user(
            username="stranger",
            email="stranger@example.com",
            password="password123",
        )
        stranger_home = Home.objects.create(owner=stranger, name="Not Mine")
        Item.objects.create(owner=stranger, name="Not Yours")

        directory = self.backup()
        payload = (directory / "data.json").read_text(encoding="utf-8")

        self.assertNotIn("Not Yours", payload)
        self.assertNotIn(stranger_home.name, payload)

    def test_restores_the_account_from_a_backup(self):
        directory = self.backup()
        Item.objects.filter(owner=self.user).delete()
        LocationNode.objects.filter(home__owner=self.user).delete()
        self.assertEqual(Item.objects.count(), 0)

        call_command(
            "seed_demo",
            fixture=str(directory / "data.json"),
            force=True,
            stdout=StringIO(),
        )

        restored = User.objects.get(username="test")
        item = Item.objects.get(owner=restored)
        self.assertEqual(item.name, "Passport")
        self.assertEqual(item.current_location_node.full_code, "LIVING-A")
        self.assertEqual(item.current_location_node.path, "Living Room / Shelf A")
        self.assertEqual(
            ItemLocationHistory.objects.filter(item__owner=restored).count(), 1
        )

    def test_prunes_backups_past_the_retention_window(self):
        stale = self.root / "demo-20200101-000000"
        stale.mkdir(parents=True)
        recent_stamp = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d-%H%M%S")
        recent = self.root / f"demo-{recent_stamp}"
        recent.mkdir(parents=True)
        unrelated = self.root / "keep-me"
        unrelated.mkdir(parents=True)

        self.backup(keep_days=14)

        self.assertFalse(stale.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(unrelated.exists())

    def test_keeps_everything_when_retention_is_disabled(self):
        stale = self.root / "demo-20200101-000000"
        stale.mkdir(parents=True)

        self.backup(keep_days=0)

        self.assertTrue(stale.exists())

    def test_reports_a_missing_account(self):
        with self.assertRaises(CommandError):
            call_command(
                "backup_demo", out=str(self.root), username="nobody", stdout=StringIO()
            )
