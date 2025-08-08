def grub_config():
	with open('/etc/default/grub','r') as file:
		data = file.readlines()
	data[5] = 'GRUB_CMDLINE_LINUX="crashkernel=auto resume=/dev/mapper/cl-swap rd.lvm.lv=cl/root rd.lvm.lv=cl/swap rhgb quiet console=ttyS0,115200 loglevel=7"\n'
	with open('/etc/default/grub', 'w') as file:
		file.writelines(data)

grub_config()
