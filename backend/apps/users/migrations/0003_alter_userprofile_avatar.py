from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_userprofile_birthday_userprofile_gender_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="avatar",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
