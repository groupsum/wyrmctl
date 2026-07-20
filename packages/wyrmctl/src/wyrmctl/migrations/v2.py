"""Schema v2 marker module.

Schema v2 adds provider-backed DNS records under dns_records. Schema v1
documents migrate by adding an empty dns_records list and updating
schemaVersion to 2.
"""

from wyrmctl.migrations.builtin import BUILTIN_MIGRATIONS

CURRENT = 2
STEP = BUILTIN_MIGRATIONS.path("DesiredState", 1, 2)[0]
