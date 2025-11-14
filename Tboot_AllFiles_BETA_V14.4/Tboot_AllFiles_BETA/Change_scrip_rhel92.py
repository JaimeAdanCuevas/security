#!/usr/bin/env python3
"""
Change_scrip_rhel92.py
Insert 'insmod relocator' right after 'insmod multiboot2' in GRUB config.
Works for RHEL 8/9 UEFI systems.
"""

import os
import sys
from datetime import datetime

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
GRUB_CFG = "/boot/efi/EFI/redhat/grub.cfg"   # Adjust if you use /boot/efi/EFI/centos/
INSERT_AFTER = "insmod multiboot2"
INSERT_LINE  = "insmod relocator"

# ----------------------------------------------------------------------
def backup_file(path):
    """Create a timestamped backup of the file."""
    if not os.path.exists(path):
        return False
    backup_path = f"{path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(path, backup_path)
        print(f"Backup created: {backup_path}")
        return True
    except Exception as e:
        print(f"Failed to create backup: {e}", file=sys.stderr)
        return False

# ----------------------------------------------------------------------
def insert_relocator():
    if not os.path.isfile(GRUB_CFG):
        print(f"ERROR: GRUB config not found: {GRUB_CFG}", file=sys.stderr)
        sys.exit(1)

    # Read the file
    try:
        with open(GRUB_CFG, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"ERROR: Cannot read {GRUB_CFG}: {e}", file=sys.stderr)
        sys.exit(1)

    # Find insertion point
    insert_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == INSERT_AFTER:
            insert_idx = i + 1
            break

    if insert_idx is None:
        print(f"WARNING: '{INSERT_AFTER}' not found in {GRUB_CFG}. Skipping.", file=sys.stderr)
        return

    # Check if already inserted (idempotency)
    if insert_idx < len(lines) and INSERT_LINE in lines[insert_idx].strip():
        print(f"'{INSERT_LINE}' already present. No changes made.")
        return

    # Insert the line (with same leading whitespace as the reference line)
    ref_indent = lines[i - (1 if i > 0 else 0)][:len(line) - len(line.lstrip())]
    new_line = f"{ref_indent}{INSERT_LINE}\n"

    lines.insert(insert_idx, new_line)

    # Backup + write
    if not backup_file(GRUB_CFG):
        sys.exit(1)

    try:
        with open(GRUB_CFG, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Successfully inserted '{INSERT_LINE}' into {GRUB_CFG}")
    except Exception as e:
        print(f"ERROR: Failed to write {GRUB_CFG}: {e}", file=sys.stderr)
        sys.exit(1)

# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("Running GRUB relocator module insertion...")
    insert_relocator()
    print("Done.")