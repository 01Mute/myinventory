"""Shared shape of the demo account's data.

seed_demo writes this shape and backup_demo reads it, so the two stay
symmetric: a backup taken today is a fixture seed_demo can load tomorrow. The
constants live here rather than in either command so neither owns them.
"""

from django.core.serializers import serialize

from homes.models import FloorPlan, Home
from items.models import Category, Item, ItemLocationHistory, ItemTag, Tag
from locations.models import LocationNode

# Ownership is stored as this placeholder rather than a real user id, so a
# fixture never depends on which user row happens to exist when it is loaded.
FIXTURE_OWNER_PK = 2

OWNER_FIELDS = ("owner", "created_by")

# Ordered from least to most dependent, so a load runs top-down.
SEEDED_MODELS = (
    Home,
    FloorPlan,
    LocationNode,
    Category,
    Tag,
    Item,
    ItemTag,
    ItemLocationHistory,
)

# How to reach the owning user from each model. Only Home, Category and Tag
# carry the user directly; everything else is owned transitively.
OWNER_LOOKUPS = {
    Home: "owner",
    FloorPlan: "home__owner",
    LocationNode: "home__owner",
    Category: "owner",
    Tag: "owner",
    Item: "owner",
    ItemTag: "item__owner",
    ItemLocationHistory: "item__owner",
}

# Fields holding a path into MEDIA_ROOT. A dump that captured only rows would
# restore items whose photos 404.
MEDIA_FIELDS = {
    Item: "photo",
    FloorPlan: "background_image",
}


def owned_queryset(model, user):
    """Every row of `model` belonging to `user`."""
    queryset = model.objects.filter(**{OWNER_LOOKUPS[model]: user})
    if model is LocationNode:
        # Parents before children, so the dump reads in tree order even though
        # deferred foreign keys mean the database would accept any order.
        return queryset.order_by("level", "id")
    return queryset.order_by("id")


def dump_objects(user):
    """Serialize the user's rows into the fixture shape seed_demo loads.

    Real owner ids are replaced with FIXTURE_OWNER_PK on the way out, which is
    exactly the substitution seed_demo reverses on the way in.
    """
    objects = []
    for model in SEEDED_MODELS:
        rows = serialize("python", owned_queryset(model, user))
        for row in rows:
            for field in OWNER_FIELDS:
                if row["fields"].get(field) == user.pk:
                    row["fields"][field] = FIXTURE_OWNER_PK
            objects.append(row)
    return objects


def media_names(user):
    """Every media file the user's rows point at, as MEDIA_ROOT-relative paths."""
    names = set()
    for model, field in MEDIA_FIELDS.items():
        for value in owned_queryset(model, user).values_list(field, flat=True):
            if value:
                names.add(value)
    return sorted(names)


def apply_owner(objects, owner_pk):
    """Point fixture rows at a real user. The inverse of dump_objects()."""
    for row in objects:
        fields = row["fields"]
        for field in OWNER_FIELDS:
            if fields.get(field) == FIXTURE_OWNER_PK:
                fields[field] = owner_pk
    return objects
