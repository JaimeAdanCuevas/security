#!/usr/bin/env python3
import sys

def check_bits(register_name, value_hex, checks):
    # Convert hex string to integer
    value = int(value_hex, 16)
    print(f"{register_name} = 0x{value:08X} -> {value:032b}")
    
    for bit, expected, desc in checks:
        actual = (value >> bit) & 1
        status = "✅" if actual == expected else "❌"
        print(f"Bit {bit} ({desc}) -> expected {expected}, actual {actual} {status}")
    print()

def main():
    if len(sys.argv) != 3:
        print("Usage: python check_hfsts.py <HFSTS4_hex> <HFSTS5_hex>")
        print("Example: python check_hfsts.py 0x00004000 0x00041F03")
        sys.exit(1)
    
    hfsts4_hex = sys.argv[1]
    hfsts5_hex = sys.argv[2]

    hfsts4_checks = [
        (12, 0, "All TPMs disconnected"),
        (15, 0, "BtG selftest failed"),
        (21, 1, "CPU Cos enabled"),
        (22, 0, "COS error"),
    ]
    
    hfsts5_checks = [
        (0, 1, "ACM active STS"),
        (8, 1, "ACM done"),
    ]
    
    check_bits("HFSTS4", hfsts4_hex, hfsts4_checks)
    check_bits("HFSTS5", hfsts5_hex, hfsts5_checks)

if __name__ == "__main__":
    main()
