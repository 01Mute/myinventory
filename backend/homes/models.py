import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def floor_plan_background_path(instance, filename):
    """Unguessable path, for the same reason as items.models.item_photo_path."""
    return f"floor-plans/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Home(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="homes",
    )
    name = models.CharField(max_length=120)
    address_optional = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_home_name_per_owner",
            ),
        ]

    def __str__(self):
        return self.name


class FloorPlan(models.Model):
    class Unit(models.TextChoices):
        PIXEL = "PX", "Pixel"
        CENTIMETER = "CM", "Centimeter"
        METER = "M", "Meter"

    home = models.ForeignKey(
        Home,
        on_delete=models.CASCADE,
        related_name="floor_plans",
    )
    name = models.CharField(max_length=120)
    width = models.PositiveIntegerField(default=1000)
    height = models.PositiveIntegerField(default=700)
    unit = models.CharField(max_length=8, choices=Unit.choices, default=Unit.PIXEL)
    background_image = models.ImageField(
        upload_to=floor_plan_background_path,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["home_id", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["home", "name"],
                name="unique_floor_plan_name_per_home",
            ),
        ]

    def __str__(self):
        return f"{self.home} - {self.name}"
