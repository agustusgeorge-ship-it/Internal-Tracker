"""Load a realistic set of demo equipment.

Usage: python manage.py seed_equipment

Safe to run more than once: items are matched on serial number, so
nothing is duplicated and existing items are left as they are.
"""

from django.core.management.base import BaseCommand

from equipment.models import Equipment

T = Equipment.Type
C = Equipment.Condition

DEMO_ITEMS = [
    ("MacBook Air 13\" M3", "LAP-MBA-0001", T.LAPTOP,
     "16 GB RAM, 512 GB SSD, macOS", C.GOOD),
    ("MacBook Pro 14\" M4", "LAP-MBP-0001", T.LAPTOP,
     "24 GB RAM, 1 TB SSD, macOS", C.GOOD),
    ("Dell XPS 13", "LAP-DXP-0001", T.LAPTOP,
     "16 GB RAM, 512 GB SSD, Windows 11", C.GOOD),
    ("Lenovo ThinkPad X1 Carbon", "LAP-TPX-0001", T.LAPTOP,
     "32 GB RAM, 1 TB SSD, Windows 11", C.FAIR),
    ("HP EliteBook 840", "LAP-HPE-0001", T.LAPTOP,
     "16 GB RAM, 256 GB SSD, Windows 11", C.BAD),
    ("Dell UltraSharp 27\" monitor", "MON-DUS-0001", T.MONITOR,
     "27 inch, 4K, USB-C", C.GOOD),
    ("LG 24\" monitor", "MON-LG-0001", T.MONITOR,
     "24 inch, Full HD, HDMI", C.FAIR),
    ("iPhone 15", "PHN-IP15-0001", T.PHONE,
     "128 GB, company SIM", C.GOOD),
    ("Samsung Galaxy S24", "PHN-SGS-0001", T.PHONE,
     "256 GB, company SIM", C.GOOD),
    ("Jabra Evolve2 65 headset", "PER-JAB-0001", T.PERIPHERAL,
     "Wireless, noise cancelling", C.GOOD),
    ("Logitech MX Keys keyboard", "PER-LMX-0001", T.PERIPHERAL,
     "Wireless, UK layout", C.GOOD),
    ("Logitech Lift vertical mouse", "PER-LFT-0001", T.PERIPHERAL,
     "Ergonomic, right-handed", C.GOOD),
    ("CalDigit TS4 dock", "INF-CDT-0001", T.INFRASTRUCTURE,
     "Thunderbolt 4, 18 ports", C.GOOD),
    ("Ubiquiti UniFi access point", "INF-UBQ-0001", T.INFRASTRUCTURE,
     "Wi-Fi 6, ceiling mount", C.FAIR),
]


class Command(BaseCommand):
    """Create the demo items that do not exist yet."""

    help = "Load demo equipment (laptops, monitors, phones and more)."

    def handle(self, *args, **options):
        """Create each missing item and report how many were added."""
        created = 0
        for name, serial, kind, spec, condition in DEMO_ITEMS:
            _, was_created = Equipment.objects.get_or_create(
                serial_number=serial,
                defaults={
                    "name": name,
                    "equipment_type": kind,
                    "specification": spec,
                    "condition": condition,
                    "status": (
                        Equipment.Status.IN_REPAIR
                        if condition == C.BAD
                        else Equipment.Status.IN_STOCK
                    ),
                    "location": "Head office store room",
                },
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(
            f"Added {created} item(s). {len(DEMO_ITEMS) - created} "
            "already existed."
        ))
