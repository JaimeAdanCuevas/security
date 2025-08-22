import sys
import struct

def find_all_rsa_modulus(ifwi_file):
    with open(ifwi_file, "rb") as f:
        data = f.read()

    marker = b"__KEYM__"
    start = 0
    found_any = False

    while True:
        idx = data.find(marker, start)
        if idx == -1:
            break

        print(f"\n[+] Key Manifest encontrado en offset 0x{idx:X}")
        km_data = data[idx:]
        data_len = len(km_data)

        # Buscar Exponent típico 0x010001
        exponent_bytes = struct.pack("<I", 0x00010001)
        found = False

        for i in range(data_len - 4):
            if km_data[i:i+4] == exponent_bytes:
                keysize_offset = i - 2
                try:
                    key_size = struct.unpack_from("<H", km_data, keysize_offset)[0]
                except struct.error:
                    continue  # ignorar si no hay suficientes bytes

                modulus_offset = i + 4
                print(f"    [+] RSA Exponent encontrado en offset absoluto 0x{idx + i:X}")
                print(f"    [+] Modulus de {key_size} bytes en offset absoluto 0x{idx + modulus_offset:X}")
                found = True
                found_any = True
                break

        if not found:
            print("    [-] No se encontró Exponent 0x010001 en este Key Manifest")

        start = idx + 1  # continuar buscando el siguiente __KEYM__

    if not found_any:
        print("[-] No se encontraron Key Manifest con RSA Exponent en todo el archivo")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Uso: python {sys.argv[0]} ifwi.bin")
        sys.exit(1)

    ifwi_file = sys.argv[1]
    find_all_rsa_modulus(ifwi_file)
