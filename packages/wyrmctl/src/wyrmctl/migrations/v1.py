"""Schema v1 marker module.

The first public schema is v1. Legacy documents with no schema header migrate by
adding apiVersion/schemaVersion and empty resource lists for missing sections.
"""

from wyrmctl.migrations.builtin import BUILTIN_MIGRATIONS

CURRENT = 1
STEP = BUILTIN_MIGRATIONS.path("DesiredState", 0, 1)[0]
