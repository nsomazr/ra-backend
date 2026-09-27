from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessment", "0002_sync_team_and_meta"),
    ]

    operations = [
        migrations.AddField(
            model_name="syncmeta",
            name="open_conflicts",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="syncmeta",
            name="presence",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
