from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from homes.models import FloorPlan, Home


class LocationNode(models.Model):
    class NodeType(models.TextChoices):
        HOME = "HOME", "Home"
        FLOOR = "FLOOR", "Floor"
        ROOM = "ROOM", "Room"
        ZONE = "ZONE", "Zone"
        FURNITURE = "FURNITURE", "Furniture"
        COMPARTMENT = "COMPARTMENT", "Compartment"
        BOX = "BOX", "Box"
        CUSTOM = "CUSTOM", "Custom"

    home = models.ForeignKey(
        Home,
        on_delete=models.CASCADE,
        related_name="location_nodes",
    )
    floor_plan = models.ForeignKey(
        FloorPlan,
        on_delete=models.CASCADE,
        related_name="location_nodes",
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
    )
    node_type = models.CharField(max_length=24, choices=NodeType.choices)
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    full_code = models.CharField(max_length=255, blank=True, db_index=True)
    path = models.CharField(max_length=1000, blank=True, db_index=True)
    level = models.PositiveIntegerField(default=0)
    geometry_json = models.JSONField(default=dict, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["home_id", "floor_plan_id", "path", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["home", "floor_plan", "parent", "code"],
                name="unique_location_code_per_parent",
            ),
            models.UniqueConstraint(
                fields=["home", "floor_plan", "code"],
                condition=Q(parent__isnull=True),
                name="unique_root_location_code",
            ),
        ]

    def __str__(self):
        return self.path or self.name

    def clean(self):
        if self.parent_id:
            if self.pk and self.parent_id == self.pk:
                raise ValidationError("A location node cannot be its own parent.")
            if self.parent.home_id != self.home_id:
                raise ValidationError("Parent node must belong to the same home.")
            if (
                self.floor_plan_id
                and self.parent.floor_plan_id
                and self.parent.floor_plan_id != self.floor_plan_id
            ):
                raise ValidationError("Parent node must belong to the same floor plan.")
            self._validate_no_parent_cycle()

        if self.floor_plan_id and self.floor_plan.home_id != self.home_id:
            raise ValidationError("Floor plan must belong to the same home.")

        duplicates = LocationNode.objects.filter(
            home=self.home,
            floor_plan=self.floor_plan,
            parent=self.parent,
            code=self.code,
        )
        if self.pk:
            duplicates = duplicates.exclude(pk=self.pk)
        if duplicates.exists():
            raise ValidationError("Code must be unique under the same parent.")

    def save(self, *args, **kwargs):
        self._set_hierarchy_fields()
        self.full_clean()
        super().save(*args, **kwargs)

    def _set_hierarchy_fields(self):
        if self.parent_id:
            self.home = self.parent.home
            if not self.floor_plan_id:
                self.floor_plan = self.parent.floor_plan
            self.level = self.parent.level + 1
            self.full_code = (
                f"{self.parent.full_code}-{self.code}"
                if self.parent.full_code
                else self.code
            )
            self.path = (
                f"{self.parent.path} / {self.name}"
                if self.parent.path
                else self.name
            )
            return

        self.level = 0
        self.full_code = self.code
        self.path = self.name

    def _validate_no_parent_cycle(self):
        parent = self.parent
        seen_ids = {self.pk} if self.pk else set()
        while parent:
            if parent.pk in seen_ids:
                raise ValidationError("Location tree cannot contain a cycle.")
            seen_ids.add(parent.pk)
            parent = parent.parent

    def get_descendant_ids(self, include_self=True):
        ids = [self.pk] if include_self and self.pk else []
        frontier = [self.pk] if self.pk else []

        while frontier:
            child_ids = list(
                LocationNode.objects.filter(parent_id__in=frontier).values_list(
                    "id",
                    flat=True,
                )
            )
            ids.extend(child_ids)
            frontier = child_ids

        return ids
