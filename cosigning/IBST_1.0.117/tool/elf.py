# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2019 Intel Corporation.
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
import subprocess
import logging
import re
from enum import Enum

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
        return "%s(sh_name=%s, sh_type=%s, sh_flags=%s, sh_addr=0x%04x, "\
               "sh_offset=0x%04x, sh_size=0x%04x, sh_link=%s, sh_info=%s, "\
               "sh_addralign=0x%04x, sh_entsize=0x%04x)" % (
                   self.__class__.__name__,
                   self.sh_name, self.sh_type, self.sh_flags, self.sh_addr,
                   self.sh_offset, self.sh_size, self.sh_link, self.sh_info,
                   self.sh_addralign, self.sh_entsize)


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
        return "%s(p_type=%s, p_offset=0x%04x, p_vaddr=0x%04x, p_paddr=0x%04x, "\
            "p_filesz=0x%04x, p_memsz=0x%04x, p_flags=%s, p_align=0x%04x)" % (
                self.__class__.__name__,
                self.p_type, self.p_offset, self.p_vaddr, self.p_paddr,
                self.p_filesz, self.p_memsz, bin(self.p_flags), self.p_align)


class SymTab:
    header = '<IIIBBH'

    class Binding(Enum):
        Local = 0
        Global = 1
        Weak = 2
        Loproc = 13
        Hiproc = 15

    def __init__(self):
        (self.st_name, self.st_value, self.st_size,
         self.st_info, self.st_other, self.st_shndx) = [0] * 6
        self.st_binding = self.Binding.Global

    def set(self, data):
        (self.st_name, self.st_value, self.st_size,
         self.st_info, self.st_other, self.st_shndx) = \
            struct.unpack(self.header, data)
        try:
            binding_value = self.st_info >> 4
            self.st_binding = self.Binding(binding_value)
        except ValueError:
            raise LibException("Improper binding type in elf file: {}".format(binding_value))
        

    @classmethod
    def size(cls):
        return struct.calcsize(cls.header)

    def __str__(self):
        return "%s(st_name=0x%04x, st_value=0x%04x, st_size=0x%04x "\
                   "st_info=0x%04x, st_other=0x%04x, st_shndx=0x%04x)" % (
                       self.__class__.__name__,
                       self.st_name, self.st_value, self.st_size,
                       self.st_info, self.st_other, self.st_shndx)


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
        return "%s(self.e_type=%r, self.e_machine=%r, self.e_version=%r)" % (
            self.__class__.__name__,
            self.e_type, self.e_machine, self.e_version)


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
        output = '\t{:31} : 0x{:X} [{}]\n\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n'\
                '\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n'\
                '\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n\t{:31} : 0x{:X}\n'\
                .format('magic_number', self.magic,
                        self.magic.to_bytes(4, 'little').decode(),
                        'me_offset', self.me_off,
                        'spi_offset', self.spi_off,
                        'code_offset', self.text_offset,
                        'code_file_size', self.text_filsz,
                        'code_memory_size', self.text_memsz,
                        'code_memory_physical_address', self.text_paddr,
                        'code_entry_point_address', self.text_start,
                        'data_offset', self.data_offset,
                        'data_file_size', self.data_filsz,
                        'data_memory_size', self.data_memsz,
                        'data_memory_physical_address', self.data_paddr)
        return output


class ElfInfo:

    def __init__(self):
        (self.entry_address, self.private_code_base_address, self.bss_size,
         self.uncompressed_private_code_size, self.section_text, self.section_rodata,
         self.section_data, self.section_bss, self.load_section, self.ie,
         self.image_text_start, self.image_text_end, self.image_ram_start, self.image_ram_end) = [0] * 14

    def __str__(self):
        return "%s(self.entry_address=0x%04x, self.private_code_base_address=0x%04x, "\
            "self.bss_size=0x%04x, self.uncompressed_private_code_size=0x%04x,\n\t"\
            "self.section_text=%s, \n\tself.section_rodata=%s, \n\tself.section_data=%s, "\
            "\n\tself.section_bss=%s, \n\tself.load_section=%s\n\tself.ie=%s)" % (
                self.__class__.__name__,
                self.entry_address, self.private_code_base_address, self.bss_size,
                self.uncompressed_private_code_size, self.section_text, self.section_rodata,
                self.section_data, self.section_bss, self.load_section, self.ie)


def check_elf_magic(file_name):
    logger.debug(file_name)
    if not os.path.isfile(file_name) and not os.access(file_name, os.R_OK):
        msg = 'File "%s" could not be opened!' % file_name
        raise LibException(msg)

    with open(file_name, mode='rb') as file:
        magic = file.read(4)
        return bool(magic == b'\x7fELF')


def check_elf_machine(file_name):
    elf32_ehdr = "<16x xx H"  # 16sHHIIIIHHHHHH

    with open(file_name, mode='rb') as file:
        header = file.read(struct.calcsize(elf32_ehdr))
        (e_machine,) = struct.unpack(elf32_ehdr, header)
        return e_machine


def find_ie_entry(file_name, module_entry, symtab, strtab):
    logger.debug('%s, %s', file_name, module_entry)
    entry = module_entry.encode('utf-8')
    address = None

    with open(file_name, mode='rb') as file:
        file.seek(strtab.sh_offset)
        sname = file.read(strtab.sh_size)

        stelement = SymTab()
        cnt = int(symtab.sh_size / stelement.size())
        for i in range(0, cnt):
            file.seek(symtab.sh_offset + i * stelement.size())
            data = file.read(stelement.size())
            stelement.set(data)
            if stelement.st_binding not in [SymTab.Binding.Global, SymTab.Binding.Local]:
                # only check global and local symbols
                continue
            name = sname[stelement.st_name:].split(b'\0')[0]
            if name == entry:
                address = stelement.st_value
                break

    if not address:
        raise LibException('Module entry "%s" not found in file "%s"!\n'
                           % (module_entry, file_name))

    return address


def scan_ie_elf32(file_name, module_entry, markers):
    with open(file_name, mode='rb') as file:
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
        except AttributeError:  # pragma: no cover
            bss_sh_size = 0  # pragma: no cover

        try:
            rodata_sh_size = einfo.section_rodata.sh_size
        except AttributeError:  # pragma: no cover
            rodata_sh_size = 0  # pragma: no cover

        try:
            data_sh_size = einfo.section_data.sh_size
        except AttributeError:
            data_sh_size = 0

        einfo.bss_size = bss_sh_size
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
        msg = '%s is not in ELF format!' % file_name
        raise LibException(msg)

    em_386 = 3
    if check_elf_machine(file_name) == em_386:
        return scan_ie_elf32(file_name, module_entry, markers)
    else:
        msg = '%s must be in Elf32 architecture!' % file_name
        raise LibException(msg)


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
        msg = '%s is not in ELF format!' % file_name
        raise LibException(msg)

    cmd = "{} {} \"{}\" \"{}\"".format(objcopy, obj_args, file_name, outfile)

    try:
        logger.debug(cmd)
        subprocess.check_call(cmd, shell=True)
    except FileNotFoundError:
        raise LibException('"objcopy" not found!\n'
                            'It is a part of BinUtils.\n'
                            'Download it from http://sourceforge.net/projects/'
                            'mingw/files/MinGW/Base/binutils/binutils-2.24/')
    except subprocess.CalledProcessError:
        raise LibException('"objcopy" not found!\n'
                            'It is a part of BinUtils.\n'
                            'Download it from http://sourceforge.net/projects/'
                            'mingw/files/MinGW/Base/binutils/binutils-2.24/')

    if not os.path.isfile(outfile) and not os.access(outfile, os.W_OK):
        msg = 'Could not open binary file - "%s"' % outfile
        raise LibException(msg)

    stat_info = os.stat(outfile)
    page_size = 4096
    padding_size = page_size - (stat_info.st_size % page_size)

    with open(outfile, mode='ab') as file:
        file.write(b'\xFF' * padding_size)


def get_elf_symbols(file_name, objdump_path, obj_args, symbol_names):
    objdump = objdump_path if objdump_path else get_objdump_path()
    if objdump is None:
        objdump = 'objdump'

    status = check_elf_magic(file_name)
    if not status:
        msg = '%s is not in ELF format!' % file_name
        raise LibException(msg)

    cmd = "{} {} {}".format(objdump, obj_args, file_name)

    try:
        result = subprocess.check_output(cmd, shell=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise LibException('Failed to run "objdump"!\n'
                            'It is a part of BinUtils.\n'
                            'Download it from http://sourceforge.net/projects/'
                            'mingw/files/MinGW/Base/binutils/binutils-2.24/')

    result = result.decode('ascii').replace("\r\n", "\n")
    regex = re.compile(r"(?P<offset>[0-9a-fA-F]{8}) .+ (?P<name>[^\s]+)$", re.MULTILINE)
    symbols = {m[1] : m[0] for m in regex.findall(result) if m[1] in symbol_names}
    return symbols
