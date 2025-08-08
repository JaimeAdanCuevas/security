def grub_relocator():
	with open('/boot/efi/EFI/centos/grub.cfg') as file_d:
		data1 = file_d.readlines()
	inx = (data1.index("\tinsmod multiboot2\n"))
	data1.insert(inx-1, "\tinsmod relocator\n")
	with open('/boot/efi/EFI/centos/grub.cfg', 'w') as file_d:
		file_d.writelines(data1)

grub_relocator()