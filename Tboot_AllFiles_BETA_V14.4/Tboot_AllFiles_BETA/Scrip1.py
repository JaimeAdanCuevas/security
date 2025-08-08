def grub_config():
	with open('/etc/default/grub','r') as file:
		data = file.readlines()
	data[5] = 'GRUB_CMDLINE_LINUX="crashkernel=auto resume=/dev/mapper/rhel00-swap rd.lvm.lv=rhel00/root rd.lvm.lv=rhel00/swap rhgb quiet console=ttyS0,115200 loglevel=7"\n'
	with open('/etc/default/grub', 'w') as file:
		file.writelines(data)

grub_config()
