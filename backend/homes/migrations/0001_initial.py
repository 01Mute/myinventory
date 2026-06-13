from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Home",
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
                ("name", models.CharField(max_length=120)),
                ("address_optional", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="homes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name", "id"],
            },
        ),
        migrations.CreateModel(
            name="FloorPlan",
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
                ("name", models.CharField(max_length=120)),
                ("width", models.PositiveIntegerField(default=1000)),
                ("height", models.PositiveIntegerField(default=700)),
                (
                    "unit",
                    models.CharField(
                        choices=[
                            ("PX", "Pixel"),
                            ("CM", "Centimeter"),
                            ("M", "Meter"),
                        ],
                        default="PX",
                        max_length=8,
                    ),
                ),
                (
                    "background_image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="floor-plans/",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "home",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="floor_plans",
                        to="homes.home",
                    ),
                ),
            ],
            options={
                "ordering": ["home_id", "name", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="home",
            constraint=models.UniqueConstraint(
                fields=("owner", "name"),
                name="unique_home_name_per_owner",
            ),
        ),
        migrations.AddConstraint(
            model_name="floorplan",
            constraint=models.UniqueConstraint(
                fields=("home", "name"),
                name="unique_floor_plan_name_per_home",
            ),
        ),
    ]
