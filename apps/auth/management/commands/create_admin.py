import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.core.roles import ROLE_ADMIN

User = get_user_model()


class Command(BaseCommand):
    help = "Create or update an admin superuser."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", default=os.environ.get("DJANGO_ADMIN_USER", "admin")
        )
        parser.add_argument(
            "--email", default=os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.com")
        )
        parser.add_argument(
            "--password", default=os.environ.get("DJANGO_ADMIN_PASSWORD")
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if not password:
            raise CommandError(
                "Password is required. Pass --password or set "
                "DJANGO_ADMIN_PASSWORD env var."
            )

        # Ensure admin group exists
        staff_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)

        user, created = User.objects.update_or_create(
            username=username,
            defaults={"email": email, "is_staff": True},
        )
        user.set_password(password)
        user.groups.add(staff_group)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created admin user '{username}' with email '{email}'."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated admin user '{username}'."))
