from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("travel", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="destination",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="destination",
            name="cover",
            field=models.URLField(blank=True),
        ),
        migrations.CreateModel(
            name="DestinationReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField()),
                ("content", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "destination",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="travel.destination"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="destination_reviews", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="destinationreview",
            constraint=models.UniqueConstraint(fields=("destination", "user"), name="unique_destination_review_per_user"),
        ),
    ]
