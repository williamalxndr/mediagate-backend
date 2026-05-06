from django.db import migrations


def keep_admin_remove_user_role(apps, schema_editor):
    group = apps.get_model("auth", "Group")
    group.objects.get_or_create(name="admin")
    group.objects.filter(name="user").delete()


def restore_user_role(apps, schema_editor):
    group = apps.get_model("auth", "Group")
    group.objects.get_or_create(name="user")


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0002_create_default_roles"),
    ]

    operations = [
        migrations.RunPython(keep_admin_remove_user_role, restore_user_role),
    ]
