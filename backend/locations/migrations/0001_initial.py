from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("homes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LocationNode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "node_type",
                    models.CharField(
                        choices=[
                            ("HOME", "Home"),
                            ("FLOOR", "Floor"),
                            ("ROOM", "Room"),
                            ("ZONE", "Zone"),
                            ("FURNITURE", "Furniture"),
                            ("COMPARTMENT", "Compartment"),
                            ("BOX", "Box"),
                            ("CUSTOM", "Custom"),
                        ],
                        max_length=24,
                    ),
                ),
                ("code", models.CharField(max_length=40)),
                ("name", models.CharField(max_length=120)),
                (
                    "full_code",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                (
                    "path",
                    models.CharField(blank=True, db_index=True, max_length=1000),
                ),
                ("level", models.PositiveIntegerField(default=0)),
                (
                    "geometry_json",
                    models.JSONField(blank=True, default=dict),
                ),
                (
                    "metadata_json",
                    models.JSONField(blank=True, default=dict),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "floor_plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="location_nodes",
                        to="homes.floorplan",
                    ),
                ),
                (
                    "home",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="location_nodes",
                        to="homes.home",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="locations.locationnode",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "home_id",
                    "floor_plan_id",
                    "path",
                    "sort_order",
                    "id",
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="locationnode",
            constraint=models.UniqueConstraint(
                fields=("home", "floor_plan", "parent", "code"),
                name="unique_location_code_per_parent",
            ),
        ),
        migrations.AddConstraint(
            model_name="locationnode",
            constraint=models.UniqueConstraint(
                condition=models.Q(("parent__isnull", True)),
                fields=("home", "floor_plan", "code"),
                name="unique_root_location_code",
            ),
        ),
    ]
