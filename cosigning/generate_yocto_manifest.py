#!/usr/bin/env python3
"""
generate_yocto_manifest.py

Usage:
  python3.8 generate_yocto_manifest.py \
    --ibst-root /path/to/ibst \
    --input /path/to/Input \
    --overrides /path/to/Overrides \
    --output /path/to/Output \
    --requirements /path/to/requirements.txt \
    --bootfile bootx64.efi \
    --kernelfile bzImage

This script:
 - creates (or reuses) a python3.8 venv and installs the requirements file
 - computes SHA256 for bootfile and kernelfile
 - converts the SHA256 hex to the "little-endian UINT32" style byte array string
 - updates the two override XML files named:
       CoSigningManifest_OS_Yocto_override.xml
       CoSigningManifest_NL_Yocto_override.xml
 - runs ibst_sign_all_internal.bat (must exist in ibst-root)
 - copies generated manifest files from output back to input (so they sit with the binaries)
"""

import argparse
import subprocess
import sys
import os
import shutil
import re
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import hashlib

# --- helpers ---------------------------------------------------------------

def run(cmd, check=True, shell=False):
    print("RUN:", " ".join(cmd) if isinstance(cmd, list) else cmd)
    res = subprocess.run(cmd, check=(check), shell=shell)
    return res.returncode

def ensure_python38_venv(venv_dir: Path, python_exe="python3.8", requirements: Path=None):
    if not venv_dir.exists():
        print(f"Creating venv at {venv_dir} using {python_exe} ...")
        run([python_exe, "-m", "venv", str(venv_dir)])
    pip = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "pip"
    if requirements and requirements.exists():
        print("Installing requirements from", requirements)
        run([str(pip), "install", "-r", str(requirements)])
    return venv_dir

def sha256_of_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def sha256_powershell(path: Path):
    # Provided for reference; we use Python computed hash (cross-platform).
    raise NotImplementedError

def convert_sha256_to_little_endian_uint32_string(hexsha: str) -> str:
    """
    Convert a 64-hex-digit SHA256 digest to the format described in the PDF:
    - Interpret the hex bytes
    - Break into 4-byte words, reverse each 4-byte chunk (little-endian word order),
      then output the hexstring uppercase without spaces.
    Example: "5681B1D3..." -> "D3B18156..." as in your doc example.
    """
    b = bytes.fromhex(hexsha)
    if len(b) != 32:
        raise ValueError("SHA256 must be 32 bytes")
    out = bytearray()
    for i in range(0, 32, 4):
        chunk = b[i:i+4]
        out += chunk[::-1]   # reverse each 4-byte word
    return out.hex().upper()

def replace_byte_array_in_xml(xml_path: Path, target_tag_name: str, new_value: str):
    """
    Replace the value="" attribute of a <byte_array ... value="..."/> that matches
    a target_tag_name heuristic. We try to be resilient by searching for first
    <byte_array ...> node.
    """
    if not xml_path.exists():
        raise FileNotFoundError(xml_path)
    # parse as text and do a safe regexp replace to preserve formatting
    text = xml_path.read_text(encoding="utf-8")
    # Find first occurrence of byte_array element with value="..."
    updated, n = re.subn(r'(<byte_array\b[^>]*\bvalue=")[0-9A-Fa-f]*(")', r'\1' + new_value + r'\2', text, count=1)
    if n == 0:
        # more robust approach: try to find value attr anywhere
        updated, n = re.subn(r'(\bvalue=")[0-9A-Fa-f]*(")', r'\1' + new_value + r'\2', text, count=1)
    if n == 0:
        raise RuntimeError(f"Could not find a byte_array/value attribute in {xml_path}")
    xml_path.write_text(updated, encoding="utf-8")
    print(f"Updated {xml_path} (replaced {n} byte_array value entries)")
    return True

# --- main ------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ibst-root", required=True, type=Path, help="Path to ibst tool root (where ibst_sign_all_internal.bat lives)")
    p.add_argument("--input", required=True, type=Path, help="Input folder where bootx64/bzImage are placed")
    p.add_argument("--overrides", required=True, type=Path, help="Overrides folder containing the 2 xml override files")
    p.add_argument("--output", required=True, type=Path, help="Output folder where ibst will put manifests")
    p.add_argument("--requirements", required=True, type=Path, help="requirements.txt file for ibst (pip -r)")
    p.add_argument("--venv", required=False, type=Path, default=Path(".venv_ibst"), help="venv dir to create/use")
    p.add_argument("--bootfile", required=False, default="bootx64.efi", help="Name of boot file in Input")
    p.add_argument("--kernelfile", required=False, default="bzImage", help="Name of kernel file in Input")
    args = p.parse_args()

    ibst_root = args.ibst_root.resolve()
    input_dir = args.input.resolve()
    overrides_dir = args.overrides.resolve()
    output_dir = args.output.resolve()
    req = args.requirements.resolve()
    venv_dir = args.venv.resolve()

    # sanity checks
    for d in [ibst_root, input_dir, overrides_dir]:
        if not d.exists():
            raise FileNotFoundError(f"Required path not found: {d}")

    # 1) ensure python3.8 venv and install requirements
    try:
        ensure_python38_venv(venv_dir, python_exe="python3.8", requirements=req)
    except Exception as e:
        print("Warning: could not create venv with python3.8 automatically:", e)
        print("Make sure python3.8 is available or create a virtualenv and run pip install -r requirements.txt manually.")
        # continue; later steps don't strictly require the venv to exist for hash conversion and xml edit.

    # 2) compute hashes
    boot_path = input_dir / args.bootfile
    kernel_path = input_dir / args.kernelfile
    if not boot_path.exists() or not kernel_path.exists():
        raise FileNotFoundError("Make sure both boot and kernel files exist in input folder.")
    print("Computing SHA256 for:", boot_path, kernel_path)
    boot_sha = sha256_of_file(boot_path)
    kernel_sha = sha256_of_file(kernel_path)
    print("SHA256 Boot:", boot_sha)
    print("SHA256 Kernel:", kernel_sha)

    # 3) convert to little-endian UINT32 string expected by the overrides
    boot_le = convert_sha256_to_little_endian_uint32_string(boot_sha)
    kernel_le = convert_sha256_to_little_endian_uint32_string(kernel_sha)
    print("Converted Boot LE:", boot_le)
    print("Converted Kernel LE:", kernel_le)

    # 4) update overrides XML files
    xml_os = overrides_dir / "CoSigningManifest_OS_Yocto_override.xml"
    xml_nl = overrides_dir / "CoSigningManifest_NL_Yocto_override.xml"

    print("Updating override XMLs...")
    replace_byte_array_in_xml(xml_os, "byte_array", boot_le)
    replace_byte_array_in_xml(xml_nl, "byte_array", kernel_le)

    # 5) run the sign script
    bat = ibst_root / "ibst_sign_all_internal.bat"
    if not bat.exists():
        # sometimes script is named with template; advise replacement
        print("Warning: ibst_sign_all_internal.bat not found at", bat)
        print("Look for ibst_sign_all_internal_template.bat and replace placeholders or ensure the path is correct.")
    else:
        # run the batch script and wait
        if os.name == "nt":
            print("Running signing batch script (Windows)...")
            run(["cmd.exe", "/c", str(bat)])
        else:
            print("Attempting to run batch script under wine or similar (UNIX). Please run this step on Windows if it fails.")
            run(["cmd.exe", "/c", str(bat)])  # fallback: only works if cmd is available

    # 6) copy manifests from output to input (so they sit next to binaries)
    if output_dir.exists():
        manifests = list(output_dir.glob("*manifest*.bin")) + list(output_dir.glob("*manifest*.xml")) + list(output_dir.glob("*.man"))
        if not manifests:
            print("No manifests found in Output folder. Check ibst output or the batch script logs.")
        else:
            for m in manifests:
                dest = input_dir / m.name
                print(f"Copying manifest {m} -> {dest}")
                shutil.copy2(m, dest)
    else:
        print("Output folder does not exist:", output_dir)

    print("Done. Next steps: flash IFWI (regular) to read OS hashes, boot to OS and verify manifest, then flash cosigned IFWI.")
    print("See README notes printed below for flashing and boot verification commands.")

if __name__ == "__main__":
    main()
