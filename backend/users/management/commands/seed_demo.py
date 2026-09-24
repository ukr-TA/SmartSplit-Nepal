"""
Create demo users (and optionally sample groups) for testing and the final demo.

    python manage.py seed_demo                      # demo friends only
    python manage.py seed_demo --owner you@mail.com # + sample groups for YOUR account
    python manage.py seed_demo --with-groups        # + sample groups for demo@smartsplit.np
    python manage.py seed_demo --owner you@mail.com --history 13  # a year of past bills and festivals

Safe to run more than once: existing users/groups are left alone.
"""

import datetime
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from common.money import from_paisa, to_paisa
from expenses.models import Expense, ExpenseSplit
from expenses.splitting import split_equal
from groups.models import Group, GroupMember
from notifications.models import Activity
from notifications.services import log_activity
from settlements.models import Settlement
from users.models import User

DEMO_PASSWORD = "SmartSplit@123"

FRIENDS = [
    ("Ram Sharma", "ram@smartsplit.np", "9800000001"),
    ("Sita Thapa", "sita@smartsplit.np", "9800000002"),
    ("Hari Gurung", "hari@smartsplit.np", "9800000003"),
    ("Mina Rai", "mina@smartsplit.np", "9800000004"),
    ("Bikash Tamang", "bikash@smartsplit.np", "9800000005"),
]
DEMO_OWNER = ("Demo User", "demo@smartsplit.np", "9800000000")


class Command(BaseCommand):
    help = "Create demo users and sample Nepal groups for SmartSplit."

    def add_arguments(self, parser):
        parser.add_argument("--owner", help="Email of an existing account to own the sample groups")
        parser.add_argument("--with-groups", action="store_true", help="Also create sample groups")
        parser.add_argument(
            "--history", type=int, default=13,
            help="Months of past bills and festival spending to add to the flat group, so the "
                 "spending forecast has something to learn from (default 13, use 0 to skip)",
        )

    def get_or_create_user(self, name, email, phone):
        user = User.objects.filter(email=email).first() or User.objects.filter(phone_number=phone).first()
        if user:
            return user, False
        return User.objects.create_user(email=email, password=DEMO_PASSWORD, full_name=name, phone_number=phone), True

    @transaction.atomic
    def handle(self, *args, **options):
        friends = []
        for name, email, phone in FRIENDS:
            user, created = self.get_or_create_user(name, email, phone)
            friends.append(user)
            self.stdout.write(f"  {'created' if created else 'exists '}  {name:<14} {email:<24} {phone}")

        if not (options["owner"] or options["with_groups"]):
            self.stdout.write(self.style.SUCCESS(
                f"\nDemo friends ready. Password for all: {DEMO_PASSWORD}\n"
                "Find them in 'Add member' by phone (e.g. 9800000001) or by name."
            ))
            return

        if options["owner"]:
            owner = User.objects.filter(email__iexact=options["owner"]).first()
            if not owner:
                raise CommandError(f"No account with email {options['owner']}. Register in the app first.")
        else:
            owner, _ = self.get_or_create_user(*DEMO_OWNER)

        ram, sita, hari, mina, bikash = friends
        today = timezone.localdate()

        self.make_group(
            owner, "College Project", "college", [ram, sita, hari],
            "Final year project expenses",
            [
                ("Printing & binding", 1800, "education", owner, 6),
                ("Arduino components", 4200, "education", ram, 5),
                ("Taxi to Pulchowk", 600, "transport", sita, 4),
                ("Lunch after presentation", 2400, "food", hari, 2),
            ],
        )
        flat = self.make_group(
            owner, "Kathmandu Flat", "roommates", [bikash, hari],
            "Baneshwor flat – monthly bills",
            [
                ("Rent – this month", 30000, "rent", owner, 15),
                ("Electricity (NEA)", 1650, "utilities", bikash, 10),
                ("Internet (WorldLink)", 1500, "utilities", hari, 9),
                ("Groceries – Bhatbhateni", 5400, "shopping", bikash, 3),
                ("Drinking water jars", 450, "utilities", owner, 1),
            ],
        )
        if flat and options["history"] > 0:
            self.add_history(flat, owner, [bikash, hari], months=options["history"])

        self.make_group(
            owner, "Friends Hangout", "friends", [ram, mina],
            "Weekend plans in Thamel",
            [
                ("Momo & thukpa", 1500, "food", mina, 1),
                ("Movie tickets – QFX", 1350, "entertainment", owner, 1),
            ],
            settle_first=True,
        )
        start = today - timedelta(days=12)
        self.make_group(
            owner, "Pokhara Trip (Sample)", "trip", [ram, sita, hari, mina],
            "Lakeside, Sarangkot & paragliding",
            [
                ("Tourist bus Kathmandu → Pokhara", 5000, "transport", sita, 12),
                ("Hotel – Lakeside (2 nights)", 12000, "hotel", owner, 12),
                ("Dinner at Lakeside", 3600, "food", ram, 12),
                ("Boating on Phewa", 1500, "entertainment", hari, 11),
                ("Breakfast", 1400, "food", mina, 11),
                ("Paragliding deposit", 2500, "entertainment", owner, 11),
                ("Taxi to Sarangkot", 1500, "transport", ram, 10),
                ("Lunch – thakali set", 2000, "food", sita, 10),
                ("Bus back to Kathmandu", 1500, "transport", hari, 10),
            ],
            dates=(start, start + timedelta(days=2)),
        )
        self.stdout.write(self.style.SUCCESS(
            f"\nSample groups ready for {owner.email}"
            + (f" (password {DEMO_PASSWORD})" if owner.email == DEMO_OWNER[1] else "")
            + f".\nDemo friends' password: {DEMO_PASSWORD}"
        ))

    # Recurring bills, with the amounts a Kathmandu flat actually pays. Used to give the
    # machine-learning spending forecast a few months of history to work from.
    MONTHLY_BILLS = [
        ("Rent", 30000, "rent", 1),
        ("Electricity (NEA)", 1500, "utilities", 8),
        ("Internet (WorldLink)", 1500, "utilities", 9),
        ("Gas cylinder", 2060, "utilities", 12),
        ("Groceries - Bhatbhateni", 5200, "shopping", 14),
        ("Vegetables from Kalimati", 900, "food", 18),
        ("Drinking water jars", 420, "utilities", 22),
        ("Momo night", 1200, "food", 25),
    ]

    def add_history(self, group, owner, members, months=6):
        """Add the same monthly bills for the past `months` months, with realistic variation."""
        import random

        rng = random.Random(2026)
        today = timezone.localdate()
        everyone = [owner] + members
        payers = everyone
        created = 0

        for back in range(months, 0, -1):
            year = today.year
            month = today.month - back
            while month <= 0:
                month += 12
                year -= 1
            for index, (desc, base, category, day) in enumerate(self.MONTHLY_BILLS):
                amount = Decimal(int(base * rng.uniform(0.88, 1.16) / 10) * 10)
                date = datetime.date(year, month, min(day, 28))
                expense = Expense.objects.create(
                    group=group, description=desc, amount=amount, category=category,
                    date=date, paid_by=payers[index % len(payers)], created_by=owner,
                )
                for uid, paisa, _ in split_equal(to_paisa(amount), [u.pk for u in everyone]):
                    ExpenseSplit.objects.create(expense=expense, user_id=uid, amount=from_paisa(paisa))
                created += 1

        # Festivals on their real dates, from the same calendar the ML model uses.
        first_day = datetime.date(today.year, today.month, 1)
        for _ in range(months):
            first_day = (first_day - datetime.timedelta(days=1)).replace(day=1)
        festivals = 0
        for key, name, start, peak in self.festival_dates(first_day, today.replace(day=1)):
            for index, (desc, low, high, category) in enumerate(self.FESTIVAL_EXTRAS.get(key, [])):
                amount = Decimal(int(rng.uniform(low, high) / 10) * 10)
                when = start + datetime.timedelta(days=rng.randint(0, max(0, (peak - start).days)))
                expense = Expense.objects.create(
                    group=group, description=desc, amount=amount, category=category,
                    date=when, paid_by=payers[(index + festivals) % len(payers)], created_by=owner,
                )
                for uid, paisa, _ in split_equal(to_paisa(amount), [u.pk for u in everyone]):
                    ExpenseSplit.objects.create(expense=expense, user_id=uid, amount=from_paisa(paisa))
                created += 1
            festivals += 1

        self.stdout.write(f"  created  {created} past expenses in {group.name} "
                          f"({months} months, {festivals} festivals)")

    # What a Kathmandu flat of three friends buys for each festival.
    FESTIVAL_EXTRAS = {
        "dashain": [("Khasi meat for Dashain", 3000, 6000, "food"),
                    ("Bus tickets home for Dashain", 3600, 6000, "transport"),
                    ("Fruits and sweets for Dashain", 1500, 3000, "food")],
        "tihar": [("Sayapatri mala and diyo", 2000, 4000, "shopping"),
                  ("Dry fruits and sweets for Tihar", 2000, 4000, "food")],
        "teej": [("Dar party for Teej", 2000, 4000, "food")],
        "new_year": [("Nepali New Year dinner", 2500, 5000, "food")],
        "holi": [("Holi colours and snacks", 1000, 2500, "entertainment")],
        "maghe_sankranti": [("Chaku, ghee and tarul", 800, 1500, "food")],
        "new_years_eve": [("New Year's Eve party", 3000, 6000, "entertainment")],
        "wedding_mangsir": [("Wedding gift envelope", 2000, 5000, "other")],
    }

    def festival_dates(self, start, end):
        """Festivals between two dates, read from ml/data/festival_calendar.csv if it is there."""
        import csv
        from pathlib import Path

        from django.conf import settings

        path = Path(settings.BASE_DIR).parent / "ml" / "data" / "festival_calendar.csv"
        if not path.exists():
            return []
        found = []
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                begin = datetime.date.fromisoformat(row["start_date"])
                peak = datetime.date.fromisoformat(row["peak_date"])
                if row["key"] in self.FESTIVAL_EXTRAS and start <= begin < end:
                    found.append((row["key"], row["festival"], begin, min(peak, end - datetime.timedelta(days=1))))
        return found

    def make_group(self, owner, name, gtype, members, description, expenses, dates=None, settle_first=False):
        if Group.objects.filter(name=name, memberships__user=owner).exists():
            self.stdout.write(f"  exists   group {name}")
            return None
        today = timezone.localdate()
        group = Group.objects.create(
            name=name, description=description, group_type=gtype, is_trip=gtype == "trip",
            start_date=dates[0] if dates else None, end_date=dates[1] if dates else None, created_by=owner,
        )
        GroupMember.objects.create(group=group, user=owner, role=GroupMember.Role.OWNER)
        log_activity(group, owner, Activity.Action.GROUP_CREATED, f"{owner.full_name} created {name}")
        for m in members:
            GroupMember.objects.create(group=group, user=m)
            log_activity(group, owner, Activity.Action.MEMBER_ADDED, f"{owner.full_name} added {m.full_name}")
        everyone = [owner] + members
        for desc, amount, category, payer, days_ago in expenses:
            date = today - timedelta(days=days_ago)
            expense = Expense.objects.create(
                group=group, description=desc, amount=Decimal(amount), category=category,
                date=date, paid_by=payer, created_by=owner,
            )
            for uid, paisa, _ in split_equal(to_paisa(amount), [u.pk for u in everyone]):
                ExpenseSplit.objects.create(expense=expense, user_id=uid, amount=from_paisa(paisa))
            log_activity(group, payer, Activity.Action.EXPENSE_ADDED,
                         f"{payer.full_name} added {desc}", amount=Decimal(amount))
        if settle_first:
            from settlements.balances import calculate_group_balances

            plan = calculate_group_balances(group).plan
            if plan:
                frm, to, paisa = plan[0]
                s = Settlement.objects.create(
                    group=group, payer_id=frm, recipient_id=to, amount=from_paisa(paisa),
                    method=Settlement.Method.CASH, channel=Settlement.Channel.CASH, created_by_id=frm,
                )
                s.mark_successful()
                log_activity(group, s.payer, Activity.Action.SETTLEMENT,
                             f"{s.payer.full_name} settled with {s.recipient.full_name} in cash", amount=s.amount)
        self.stdout.write(f"  created  group {name} ({len(expenses)} expenses)")
        return group
