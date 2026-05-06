from django.db import migrations


def create_default_roles(apps, schema_editor):
    group = apps.get_model("auth", "Group")
    for role in ("admin", "user"):
        group.objects.get_or_create(name=role)


def remove_default_roles(apps, schema_editor):
    group = apps.get_model("auth", "Group")
    group.objects.filter(name__in=("admin", "user")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_roles, remove_default_roles),
    ]
