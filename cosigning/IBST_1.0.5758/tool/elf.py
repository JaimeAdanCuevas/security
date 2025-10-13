# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""


import os
import struct
import subprocess  # nosec - paths to objcopy / objdump are not configurable (they're determined in code)
import logging
import re
from enum import Enum

from .FileOpener import open_file
from .LibException import LibException


logger = logging.getLogger('Lib')


class ElfSection:
    Elf32_Shdr = "<IIIIIIIIII"

    def __init__(self):
        (self.sh_name, self.sh_type, self.sh_flags, self.sh_addr,
         self.sh_offset, self.sh_size, self.sh_link, self.sh_info,
         self.sh_addralign, self.sh_entsize) = [0] * 10

    def set(self, data):
        (self.sh_name, self.sh_type, self.sh_flags, self.sh_addr,
         self.sh_offset, self.sh_size, self.sh_link, self.sh_info,
         self.sh_addralign, self.sh_entsize) = struct.unpack(self.Elf32_Shdr, data)

    @classmethod
    def size(cls):
        return struct.calcsize(cls.Elf32_Shdr)

    def __str__(self):
        return f"{self.__class__.__name__}(sh_name={self.sh_name}, sh_type={self.sh_type}, sh_flags={self.sh_flags}, " \
               f"sh_addr={self.sh_addr:#06x}, sh_offset={self.sh_offset:#06x}, sh_size={self.sh_size:#06x}, " \
               f"sh_link={self.sh_link}, sh_info={self.sh_info}, sh_addralign={self.sh_addralign:#06x}, " \
               f"sh_entsize={self.sh_entsize:#06x})"


class ElfProgramHeader:
    Elf32_Phdr = "<IIIIIIII"

    def __init__(self):
        (self.p_type, self.p_offset, self.p_vaddr, self.p_paddr,
         self.p_filesz, self.p_memsz, self.p_flags, self.p_align) = [0] * 8

    def set(self, data):
        (self.p_type, self.p_offset, self.p_vaddr, self.p_paddr,
         self.p_filesz, self.p_memsz, self.p_flags,
         self.p_align) = struct.unpack(self.Elf32_Phdr, data)

    @classmethod
    def size(cls):
        return struct.calcsize(cls.Elf32_Phdr)

    def __str__(self):
        return f"{self.__class__.__name__}(p_type={self.p_type}, p_offset={self.p_offset:#06x}, " \
               f"p_vaddr={self.p_vaddr:#06x}, p_paddr={self.p_paddr:#06x}, p_filesz={self.p_filesz:#06x}, " \
               f"p_memsz={self.p_memsz:#06x}, p_flags={bin(self.p_flags)}, p_align={self.p_align:#06x})"


class SymTab:
    header = '<IIIBBH'

    class Binding(Enum):
        LOCAL = 0
        GLOBAL = 1
        WEAK = 2
        LOPROC = 13
        HIPROC = 15

    def __init__(self):
        (self.st_name, self.st_value, self.st_size,
         self.st_info, self.st_other, self.st_shndx) = [0] * 6
        self.st_binding = self.Binding.GLOBAL

    def set(self, data):
        (self.st_name, self.st_value, self.st_size,
         self.st_info, self.st_other, self.st_shndx) = \
            struct.unpack(self.header, data)
        binding_value = self.st_info >> 4
        try:
            self.st_binding = self.Binding(binding_value)
        except ValueError as e:
            raise LibException(f"Improper binding type in elf file: {binding_value}") from e

    @classmethod
    def size(cls):
        return struct.calcsize(cls.header)

    def __str__(self):
        return f"{self.__class__.__name__}(st_name={self.st_name:#06x}, st_value={self.st_value:#06x}, " \
               f"st_size={self.st_size:#06x} st_info={self.st_info:#06x}, st_other={self.st_other:#06x}, " \
               f"st_shndx={self.st_shndx:#06x})"


class Elf32:
    Elf32_Ehdr = "<16sHHIIIIIHHHHHH"

    def __init__(self):
        (self.e_ident, self.e_type, self.e_machine, self.e_version,
         self.e_entry, self.e_phoff, self.e_shoff,
         self.e_flags, self.e_ehsize, self.e_phentsize, self.e_phnum,
         self.e_shentsize, self.e_shnum, self.e_shstrndx) = [0] * 14
        self.e_ident = b'\x00' * 16

    def set(self, data):
        (self.e_ident, self.e_type, self.e_machine, self.e_version,
         self.e_entry, self.e_phoff, self.e_shoff,
         self.e_flags, self.e_ehsize, self.e_phentsize, self.e_phnum,
         self.e_shentsize, self.e_shnum, self.e_shstrndx) = \
            struct.unpack(self.Elf32_Ehdr, data)

    @classmethod
    def size(cls):
        return struct.calcsize(cls.Elf32_Ehdr)

    def __str__(self):
        return f"{self.__class__.__name__}(self.e_type={repr(self.e_type)}, self.e_machine={repr(self.e_machine)}, " \
               f"self.e_version={repr(self.e_version)})"


class IeAttrInfo:
    IeAttrInfoHeader = "<12I"

    def __init__(self):
        (self.magic, self.me_off, self.spi_off, self.text_offset,
         self.text_filsz, self.text_memsz, self.text_paddr, self.text_start,
         self.data_offset, self.data_filsz, self.data_memsz, self.data_paddr) = [0] * 12

    def set(self, data):
        (self.magic, self.me_off, self.spi_off, self.text_offset,
         self.text_filsz, self.text_memsz, self.text_paddr, self.text_start,
         self.data_offset, self.data_filsz, self.data_memsz, self.data_paddr) = \
            struct.unpack(self.IeAttrInfoHeader, data)

    def get(self):
        data = struct.pack(self.IeAttrInfoHeader, self.magic, self.me_off, self.spi_off,
                           self.text_offset, self.text_filsz, self.text_memsz, self.text_paddr,
                           self.text_start, self.data_offset, self.data_filsz, self.data_memsz,
                           self.data_paddr)
        return data

    @classmethod
    def size(cls):
        return struct.calcsize(cls.IeAttrInfoHeader)

    def __str__(self):
        return f'\t{"magic_number":31} : 0x{self.magic:X} [{self.magic.to_bytes(4, "little").decode()}]\n\t' \
               f'{"me_offset":31} : 0x{self.me_off:X}\n\t{"spi_offset":31} : 0x{self.spi_off:X}\n\t' \
               f'{"code_offset":31} : 0x{self.text_offset:X}\n\t{"code_file_size":31} : 0x{self.text_filsz:X}\n\t' \
               f'{"code_memory_size":31} : 0x{self.text_memsz:X}\n\t{"code_memory_physical_address":31} : ' \
               f'0x{self.text_paddr:X}\n\t{"code_entry_point_address":31} : 0x{self.text_start:X}\n\t' \
               f'{"data_offset":31} : 0x{self.data_offset:X}\n\t{"data_file_size":31} : 0x{self.data_filsz:X}\n\t' \
               f'{"data_memory_size":31} : 0x{self.data_memsz:X}\n\t{"data_memory_physical_address":31} : ' \
               f'0x{self.data_paddr:X}\n'


class ElfInfo:

    def __init__(self):
        (self.entry_address, self.private_code_base_address, self.bss_size, self.text_size,
         self.uncompressed_private_code_size, self.section_text, self.section_rodata,
         self.section_data, self.section_bss, self.load_section, self.ie,
         self.image_text_start, self.image_text_end, self.image_ram_start, self.image_ram_end) = [0] * 15

    def __str__(self):
        return f"{self.__class__.__name__}(self.entry_address={self.entry_address:#06x}, " \
               f"self.private_code_base_address={self.private_code_base_address:#06x}, " \
               f"self.bss_size={self.bss_size}:#06x, self.uncompressed_private_code_size=" \
               f"{self.uncompressed_private_code_size:#06x},\n\tself.section_text={self.section_text}, \n\t" \
               f"self.section_rodata={self.section_rodata}, \n\tself.section_data={self.section_data}, \n\t" \
               f"self.section_bss={self.section_bss}, \n\tself.load_section={self.load_section}\n\tself.ie={self.ie})"


def check_elf_magic(file_name):
    logger.debug(file_name)
    if not os.path.isfile(file_name) and not os.access(file_name, os.R_OK):
        raise LibException(f'File "{file_name}" could not be opened!')

    with open_file(file_name, mode='rb') as file:
        magic = file.read(4)
        return bool(magic == b'\x7fELF')


def check_elf_machine(file_name):
    elf32_ehdr = "<16x xx H"  # 16sHHIIIIHHHHHH

    with open_file(file_name, mode='rb') as file:
        header = file.read(struct.calcsize(elf32_ehdr))
        (e_machine,) = struct.unpack(elf32_ehdr, header)
        return e_machine


def find_ie_entry(file_name, module_entry, symtab, strtab):
    logger.debug('%s, %s', file_name, module_entry)
    entry = module_entry.encode('utf-8')
    address = None

    with open_file(file_name, mode='rb') as file:
        file.seek(strtab.sh_offset)
        sname = file.read(strtab.sh_size)

        stelement = SymTab()
        cnt = int(symtab.sh_size / stelement.size())
        for i in range(0, cnt):
            file.seek(symtab.sh_offset + i * stelement.size())
            data = file.read(stelement.size())
            stelement.set(data)
            if stelement.st_binding not in [SymTab.Binding.GLOBAL, SymTab.Binding.LOCAL]:
                # only check global and local symbols
                continue
            name = sname[stelement.st_name:].split(b'\0')[0]
            if name == entry:
                address = stelement.st_value
                break

    if not address:
        raise LibException(f'Module entry "{module_entry}" not found in file "{file_name}"!\n')

    return address


def scan_ie_elf32(file_name, module_entry, markers):
    with open_file(file_name, mode='rb') as file:
        elf = Elf32()
        data = file.read(struct.calcsize(elf.Elf32_Ehdr))
        elf.set(data)

        einfo = ElfInfo()

        shdr_strtab = elf.e_shoff + elf.e_shstrndx * elf.e_shentsize
        file.seek(shdr_strtab)
        data = file.read(elf.e_shentsize)
        elfsection = ElfSection()
        elfsection.set(data)

        file.seek(elfsection.sh_offset)
        sname = file.read(elfsection.sh_size)

        for i in range(elf.e_shnum):
            file.seek(elf.e_shoff + i * elf.e_shentsize)
            sec = file.read(elf.e_shentsize)
            elfsection = ElfSection()
            elfsection.set(sec)

            name = sname[elfsection.sh_name:].split(b'\0')[0]

            if name == b'.text' or name == b'text':
                einfo.section_text = elfsection
            elif name == b'.rodata' or name == b'rodata':
                einfo.section_rodata = elfsection
            elif name == b'.data' or name == b'data':
                einfo.section_data = elfsection
            elif name == b'.bss' or name == b'bss':
                einfo.section_bss = elfsection
            elif name == b'.symtab' or name == b'symtab':
                symtab = elfsection
            elif name == b'.strtab' or name == b'strtab':
                strtab = elfsection

        einfo.entry_address = find_ie_entry(file_name, module_entry, symtab, strtab)

        pf_r = 0x4
        pf_w = 0x2
        pf_x = 0x1
        einfo.ie = IeAttrInfo()
        for i in range(elf.e_phnum):
            file.seek(elf.e_phoff + i * elf.e_phentsize)
            sec = file.read(elf.e_phentsize)
            psection = ElfProgramHeader()
            psection.set(sec)

            if psection.p_type == 0x01:  # PT_LOAD = 0x01
                if (elf.e_phnum == 1) or ((psection.p_flags & (pf_r | pf_w | pf_x)) ==
                                          (pf_r | pf_w | pf_x)):
                    einfo.ie.text_filsz = psection.p_filesz
                    einfo.ie.text_memsz = psection.p_memsz
                    einfo.ie.text_paddr = psection.p_paddr
                    einfo.ie.text_offset = psection.p_offset
                    einfo.ie.text_start = einfo.ie.text_paddr

                    einfo.ie.data_offset = einfo.ie.text_offset
                    einfo.ie.data_filsz = einfo.ie.text_filsz
                    einfo.ie.data_memsz = 0
                    einfo.ie.data_paddr = 0
                elif (psection.p_flags & (pf_r | pf_x)) == (pf_r | pf_x):
                    einfo.ie.text_filsz = psection.p_filesz
                    einfo.ie.text_memsz = psection.p_memsz
                    einfo.ie.text_paddr = psection.p_paddr
                    einfo.ie.text_offset = psection.p_offset
                    einfo.ie.text_start = einfo.ie.text_paddr
                else:
                    einfo.ie.data_offset = psection.p_offset
                    einfo.ie.data_filsz = psection.p_filesz
                    einfo.ie.data_memsz = psection.p_memsz
                    einfo.ie.data_paddr = psection.p_vaddr

        einfo.private_code_base_address = einfo.section_text.sh_addr

        try:
            bss_sh_size = einfo.section_bss.sh_size
        except AttributeError:  # pragma: no cover, due to testing with binary file. Update needed.
            bss_sh_size = 0  # pragma: no cover, due to testing with binary file. Update needed.

        try:
            rodata_sh_size = einfo.section_rodata.sh_size
        except AttributeError:  # pragma: no cover, due to testing with binary file. Update needed.
            rodata_sh_size = 0  # pragma: no cover, due to testing with binary file. Update needed.

        try:
            data_sh_size = einfo.section_data.sh_size
        except AttributeError:
            data_sh_size = 0

        try:
            text_sh_size = einfo.section_text.sh_size
        except AttributeError:  # pragma: no cover, due to testing with binary file. Update needed.
            text_sh_size = 0  # pragma: no cover, due to testing with binary file. Update needed.

        einfo.bss_size = bss_sh_size
        einfo.text_size = text_sh_size
        einfo.uncompressed_private_code_size = einfo.section_text.sh_size + \
            rodata_sh_size + data_sh_size

        if markers:
            for key, value in markers.items():
                if value is None:
                    continue
                offset = find_ie_entry(file_name, value, symtab, strtab)
                setattr(einfo, key, offset)

        return einfo


def scan_ie_elf(file_name, module_entry, markers):
    status = check_elf_magic(file_name)
    if not status:
        raise LibException(f'{file_name} is not in ELF format!')

    em_386 = 3
    if check_elf_machine(file_name) == em_386:
        return scan_ie_elf32(file_name, module_entry, markers)
    raise LibException(f'{file_name} must be in Elf32 architecture!')


def scan_elf_with_objdump(file_name, objdump_path, objdump_args, symbols_map):
    elf_symbols = get_elf_symbols(file_name, objdump_path, objdump_args, list(symbols_map.values()))

    einfo = ElfInfo()

    # symbols_map maps relation: attribute name in ElfInfo stricture <-> name in elf file
    # elf_symbols maps relation: name in elf file <-> offset value
    # we need to create relation: attribute name <-> offset (not in map but in ElfInfo structure)
    for symbol in symbols_map:
        if symbols_map[symbol] in elf_symbols:
            setattr(einfo, symbol, int(elf_symbols[symbols_map[symbol]], 16))
        else:
            raise LibException(f"Missing '{symbols_map[symbol]}' in '{file_name}'")

    return einfo


def get_external_tool_path(tool_name):
    wdir = os.path.dirname(os.path.realpath(__file__))
    possible_paths = [os.path.join(wdir, tool_name),
                      os.path.join(wdir, tool_name + '.exe'),
                      os.path.join(wdir, '../' + tool_name),
                      os.path.join(wdir, '../' + tool_name + '.exe')]

    for p in possible_paths:
        if os.path.exists(p):
            return os.path.normpath(p)

    return None


def get_objcopy_path():
    return get_external_tool_path('objcopy')


def get_objdump_path():
    return get_external_tool_path('objdump')


def ie_elf2bin(file_name, objcopy_path, obj_args, outfile):
    logger.debug('%s, %s', file_name, outfile)
    objcopy = objcopy_path if objcopy_path else get_objcopy_path()
    if objcopy is None:
        objcopy = 'objcopy'

    status = check_elf_magic(file_name)
    if not status:
        raise LibException(f'{file_name} is not in ELF format!')

    obj_args = [i for i in re.split("( |\\\".*?\\\"|'.*?')", obj_args) if i.strip()]
    cmd = [objcopy] + obj_args + [file_name, outfile]

    try:
        logger.debug(cmd)
        subprocess.check_call(cmd, shell=False)  # nosec - path is not configurable, args are hardly configurable in xml (user can enable a fixed additional option)
    except FileNotFoundError as e:
        raise LibException('"objcopy" not found!\n'
                           'It is a part of BinUtils.\n'
                           'Download it from http://sourceforge.net/projects/'
                           'mingw/files/MinGW/Base/binutils/binutils-2.24/') from e
    except subprocess.CalledProcessError as e:
        raise LibException('"objcopy" not found!\n'
                           'It is a part of BinUtils.\n'
                           'Download it from http://sourceforge.net/projects/'
                           'mingw/files/MinGW/Base/binutils/binutils-2.24/') from e

    if not os.path.isfile(outfile) and not os.access(outfile, os.W_OK):
        raise LibException(f'Could not open binary file - "{outfile}"')

    stat_info = os.stat(outfile)
    page_size = 4096
    padding_size = page_size - (stat_info.st_size % page_size)

    with open_file(outfile, mode='ab') as file:
        file.write(b'\xFF' * padding_size)


def get_elf_symbols(file_name, objdump_path, obj_args, symbol_names):
    objdump = objdump_path if objdump_path else get_objdump_path()
    if objdump is None:
        objdump = 'objdump'

    status = check_elf_magic(file_name)
    if not status:
        raise LibException(f'{file_name} is not in ELF format!')

    obj_args = [i for i in re.split("( |\\\".*?\\\"|'.*?')", obj_args) if i.strip()]
    cmd = [objdump]+obj_args+[file_name]

    try:
        result = subprocess.check_output(cmd, shell=False)  # nosec - path is not configurable, neither are args
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise LibException('Failed to run "objdump"!\n'
                           'It is a part of BinUtils.\n'
                           'Download it from http://sourceforge.net/projects/'
                           'mingw/files/MinGW/Base/binutils/binutils-2.24/') from e

    result = result.decode('ascii').replace("\r\n", "\n")
    regex = re.compile(r"(?P<offset>[0-9a-fA-F]{8}) .+ (?P<name>[^\s]+)$", re.MULTILINE)
    symbols = {m[1]: m[0] for m in regex.findall(result) if m[1] in symbol_names}
    return symbols
