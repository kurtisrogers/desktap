from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.dev_fixture_data import (
    DEV_PASSWORD,
    SEED_USERNAMES,
    create_verified_adult,
    credential_summary,
    enroll_totp,
)
from accounts.models import ParentChildLink, User, UserRole
from moderation.models import ContentReport, ReportStatus
from posts.models import Comment, Follow, Post


class Command(BaseCommand):
    help = "Load local development fixtures with known passwords and 2FA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded users and their content before loading.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running when DEBUG=False (not recommended).",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_dev only runs with DEBUG=True. Use --force to override (not recommended)."
            )

        if options["flush"]:
            self._flush_seed_data()

        with transaction.atomic():
            users = self._create_users()
            posts = self._create_social_graph(users)
            self._create_moderation_sample(users, posts)

        self.stdout.write(self.style.SUCCESS("Development fixtures loaded."))
        self.stdout.write(credential_summary())

    def _flush_seed_data(self):
        usernames = list(SEED_USERNAMES)
        deleted, _ = User.objects.filter(username__in=usernames).delete()
        self.stdout.write(self.style.WARNING(f"Flushed {deleted} seeded object(s)."))

    def _create_users(self) -> dict[str, User]:
        superadmin, _ = User.objects.get_or_create(
            username="superadmin",
            defaults={
                "email": "superadmin@desktap.local",
                "display_name": "Site Superadmin",
                "role": UserRole.SUPERADMIN,
                "card_verified": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        superadmin.set_password(DEV_PASSWORD)
        superadmin.role = UserRole.SUPERADMIN
        superadmin.card_verified = True
        superadmin.is_staff = True
        superadmin.is_superuser = True
        superadmin.is_suspended = False
        superadmin.save()
        enroll_totp(superadmin)

        support, _ = User.objects.get_or_create(
            username="support",
            defaults={
                "email": "support@desktap.local",
                "display_name": "Support Agent",
                "role": UserRole.SUPPORT,
                "card_verified": True,
                "is_staff": True,
            },
        )
        support.set_password(DEV_PASSWORD)
        support.role = UserRole.SUPPORT
        support.card_verified = True
        support.is_staff = True
        support.is_suspended = False
        support.save()
        enroll_totp(support)

        alex = create_verified_adult(
            username="alex",
            email="alex@desktap.local",
            display_name="Alex Morgan",
            bio="Building healthier online habits, one desktop session at a time.",
            date_of_birth=date(1992, 6, 12),
        )
        riley = create_verified_adult(
            username="riley",
            email="riley@desktap.local",
            display_name="Riley Chen",
            bio="Prefers keyboards to touchscreens.",
            date_of_birth=date(1988, 3, 22),
        )
        jamie = create_verified_adult(
            username="jamie_parent",
            email="jamie@desktap.local",
            display_name="Jamie Parent",
            bio="Parent account for local testing.",
            date_of_birth=date(1985, 9, 4),
            is_parent=True,
        )

        sam, created = User.objects.get_or_create(
            username="sam_child",
            defaults={
                "email": "sam@desktap.local",
                "display_name": "Sam",
                "bio": "Student account linked to a parent.",
                "date_of_birth": date(2012, 11, 8),
                "role": UserRole.CHILD,
                "parent_account": jamie,
                "card_verified": True,
            },
        )
        if created:
            sam.set_password(DEV_PASSWORD)
            sam.save()
        else:
            sam.role = UserRole.CHILD
            sam.parent_account = jamie
            sam.card_verified = True
            sam.is_suspended = False
            sam.set_password(DEV_PASSWORD)
            sam.save()
        enroll_totp(sam)

        ParentChildLink.objects.update_or_create(
            parent=jamie,
            child=sam,
            defaults={"child_disabled": False},
        )

        return {
            "superadmin": superadmin,
            "support": support,
            "alex": alex,
            "riley": riley,
            "jamie": jamie,
            "sam": sam,
        }

    def _create_social_graph(self, users: dict[str, User]) -> list[Post]:
        alex = users["alex"]
        riley = users["riley"]
        sam = users["sam"]

        Follow.objects.get_or_create(follower=alex, following=riley)
        Follow.objects.get_or_create(follower=riley, following=alex)
        Follow.objects.get_or_create(follower=alex, following=sam)

        post_specs = [
            (alex, "First post on Desktap — glad to be here away from my phone."),
            (riley, "Coffee, keyboard, and a calm feed. This is the vibe."),
            (sam, "Finished homework early today. Reading comments on desktop only."),
            (alex, "Parents: the safety tools here actually make sense."),
        ]

        posts: list[Post] = []
        for author, content in post_specs:
            post, _ = Post.objects.get_or_create(author=author, content=content)
            posts.append(post)

        Comment.objects.get_or_create(
            post=posts[0],
            author=riley,
            defaults={"content": "Welcome! The desktop-only rule is refreshing."},
        )
        Comment.objects.get_or_create(
            post=posts[2],
            author=users["jamie"],
            defaults={"content": "Proud of you for staying safe online."},
        )

        posts[0].likes.add(riley, sam)
        posts[1].likes.add(alex)
        return posts

    def _create_moderation_sample(self, users: dict[str, User], posts: list[Post]):
        ContentReport.objects.get_or_create(
            reporter=users["riley"],
            content_type="post",
            content_id=posts[2].pk,
            defaults={
                "reason": "other",
                "details": "Sample open report for staff queue testing.",
                "status": ReportStatus.OPEN,
            },
        )
