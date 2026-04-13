from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_alter_userprofile_avatar"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="travel_level",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
    ]
