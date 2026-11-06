"""Private, unlisted or public: `visibility` replaces `is_public`, and an
unlisted pack gets a share link (`share_token`). Public packs stay public."""

from django.db import migrations, models


def copy_is_public(apps, schema_editor):
    Pack = apps.get_model("packs", "Pack")
    Pack.objects.filter(is_public=True).update(visibility="public")


def copy_visibility_back(apps, schema_editor):
    Pack = apps.get_model("packs", "Pack")
    Pack.objects.filter(visibility="public").update(is_public=True)


class Migration(migrations.Migration):
    dependencies = [
        ("packs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pack",
            name="visibility",
            field=models.CharField(
                choices=[("private", "Private"), ("unlisted", "Unlisted"), ("public", "Public")],
                db_index=True,
                default="private",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="pack",
            name="share_token",
            field=models.CharField(
                blank=True, editable=False, max_length=64, null=True, unique=True
            ),
        ),
        migrations.RunPython(copy_is_public, copy_visibility_back),
        migrations.RemoveField(
            model_name="pack",
            name="is_public",
        ),
    ]
