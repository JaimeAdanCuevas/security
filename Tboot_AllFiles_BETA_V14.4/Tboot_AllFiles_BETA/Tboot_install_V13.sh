#!/bin/bash
#THIS FILE 
#
#For a safe installation of this file, give it all permissions, run
#'chmod 777 Test-CentOS.sh' or 'chmod +x Test-CentOS.sh'.
#
#To run the command on a terminal Linux'./Test-CentOS.sh'.
#
#If you have any errors or question about this file, please contact
#Jose Lucero Hernandez.

# Intel proxy configuration
export http_proxy="http://proxy-dmz.intel.com:912"
export https_proxy="http://proxy-dmz.intel.com:912"
export ftp_proxy="http://proxy-dmz.intel.com:911"
export socks_proxy="http://proxy-us.intel.com:1080"
export no_proxy="intel.com,.intel.com,localhost,127.0.0.1"

echo -n "Select your OS --> 1.CentOS, 2.RHEL8, 3.SLES, 4.RHEL9.2: "
read VAR
if [[ $VAR -eq 1 ]]
then
cp Proxy_Centos.sh /etc/profile.d
echo "Copying Proxy_Centos.sh"
dhclient 
bash NetworkPatch_IT_script.sh
sleep 2
rm /etc/yum.repo.d/* -f
echo "cleaning previuos repos..."
sleep 1
cp CentOS-Linux-ContinuousRelease.repo /etc/yum.repos.d/
cp CentOS-Linux-BaseOS.repo /etc/yum.repos.d/
cp CentOS-Linux-AppStream.repo /etc/yum.repos.d/
cp CentOS-Linux-PowerTools.repo /etc/yum.repos.d/
echo "Installing Repos on /etc/yum.repos.d"
echo "If the installation doesn't continue after 10 seconds please stop this scrip and do a reboot"
sleep 2
yum install python3 python3-devel openssl-devel grub2-efi-modules xterm tpm-tools tpm2-tools mercurial -y
yum install python2 python2-devel gtk2-devel gtk3-devel libxslt-devel -y
dnf -y --enablerepo=powertools install trousers-devel
echo "If the installation doesn't continue after 10 seconds please stop this scrip and do a reboot"
sleep 2
pip3 install pyasn1
yum install swig -y
pip3 install m2crypto
dnf install grub2-efi-x64-modules -y
echo "Creating necessary folders...."
sleep 2
cp -r /usr/lib/grub/x86_64-efi /boot/efi/EFI/centos/
cp volatility /usr/local/sbin
chmod 777 /usr/local/sbin/volatility
cp -r val_tools /root/
echo "Installing Val_Tools..."
sleep 2
chmod 777 val_tools/SIV/NonProjectSpecific/TestContent/*
ln -s /root/val_tools /usr/local/val_tools
echo "Installing Tboot..."
sleep 2
tar -zxvf tboot-1.10.5.tar.gz
cd tboot-1.10.5
make all
make install
cd ..
echo "Creating a new grub..."
grub2-mkconfig -o /boot/efi/EFI/centos/grub.cfg
python3 Change_scrip_centos.py
chmod +x /boot/efi/EFI/centos/grub.cfg
echo "Installation Complete"
elif [[ $VAR -eq 2 ]]
then
cp proxy.sh /etc/profile.d 
echo "Copying Proxy.sh"
sleep 3
bash NetworkPatch_IT_script.sh
cp intel-yum8_4.repo /etc/yum.repos.d/
echo "Copying Repos..."
sleep 3
echo "If the installation doesn't continue after 10 seconds please stop this scrip and do a reboot"
sleep 3
yum install openssl-devel trousers-devel grub2-efi-modules xterm tpm-tools tpm2-tools mercurial -y
yum install python2 python2-devel gtk2-devel gtk3-devel libxslt-devel -y
pip3 install pyasn1
yum install swig -y
pip3 install m2crypto
dnf install grub2-efi-x64-modules -y
echo "Creating necessary folders...."
sleep 2
cp -r /usr/lib/grub/x86_64-efi /boot/efi/EFI/redhat/x86_64-efi
cp volatility /usr/local/sbin
chmod 777 /usr/local/sbin/volatility
echo "Installing Val_Tools..."
sleep 2
cp -r val_tools /root/
chmod 777 val_tools/SIV/NonProjectSpecific/TestContent/*
ln -s /root/val_tools /usr/local/val_tools
echo "Installing Tboot..."
sleep 2
tar -zxvf tboot-1.10.5.tar.gz
cd tboot-1.10.5
make all
make install
cd ..
grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg
python3 Change_scrip.py
chmod +x /boot/efi/EFI/redhat/grub.cfg
echo "Installation Complete"
elif [[ $VAR -eq 3 ]]
then
echo "WARNING: please set the USB as repository before run"
sleep 10
sleep 3
echo "If the installation doesn't continue after 10 seconds please stop this scrip and do a reboot"
zypper --non-interactive in openssl grub2 trousers-devel xterm tpm-tools tpm2.0-tools mercurial python python2-pip python3-pip zlib-devel
cp volatility /usr/local/sbin
chmod 777 /usr/local/sbin/volatility
echo "Installing Val_Tools..."
sleep 2
cp -r val_tools /root/
chmod 777 val_tools/SIV/NonProjectSpecific/TestContent/*
ln -s /root/val_tools /usr/local/val_tools
tar -zxvf tboot-1.10.5.tar.gz
cd tboot-1.10.5
echo "Installing Tboot..."
sleep 2
make all
make install
cd ..
grub2-mkconfig -o /boot/grub2/grub.cfg
echo "Installation Complete"
elif [[ $VAR -eq 4 ]]; then
    echo "=== RHEL 9.2 (No USB) ==="

    # Proxy
    cp proxy.sh /etc/profile.d/
    echo "Copying proxy.sh"
    source /etc/profile.d/proxy.sh

    # Network patch
    bash NetworkPatch_IT_script.sh || { echo "Network patch failed"; exit 1; }

    # Backup & clean old repos
    [ -d /etc/yum.repos.d ] && mv /etc/yum.repos.d /etc/yum.repos.d.bak.$(date +%s)
    mkdir -p /etc/yum.repos.d

    # Copy pre-made repo file
    if [[ -f rhel92-local.repo ]]; then
        cp rhel92-local.repo /etc/yum.repos.d/
        echo "Copied rhel92-local.repo"
        dnf clean all
        dnf makecache
    else
        echo "ERROR: rhel92-local.repo not found! Using subscription-manager fallback."
        # Optional: auto-register (uncomment if needed)
        # read -p "RHN Username: " RH_USER
        # read -s -p "RHN Password: " RH_PASS; echo
        # subscription-manager register --username "$RH_USER" --password "$RH_PASS" --auto-attach
        # subscription-manager repos --enable codeready-builder-for-rhel-9-$(arch)-rpms
    fi

    echo "If the installation doesn't continue after 10 seconds please stop this script and do a reboot"
    sleep 2

    # Install packages
    dnf install -y python3 python3-devel grub2-efi-x64-modules grub2-efi-x64 openssl-devel grub2-efi-modules xterm tpm-tools tpm2-tools mercurial
    dnf install -y python3-pip swig gtk3-devel libxslt-devel

    dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
    #dnf config-manager --set-enabled crb
    dnf install -y trousers-devel

    pip3 install --trusted-host pypi.python.org pyasn1 m2crypto

    # Volatility
    cp volatility /usr/local/sbin/
    chmod 755 /usr/local/sbin/volatility

    # val_tools
    echo "Installing val_tools..."
    sleep 2
    cp -r val_tools /root/
    chmod 755 /root/val_tools/SIV/NonProjectSpecific/TestContent/*
    ln -s /root/val_tools /usr/local/val_tools

    # tboot
    echo "Installing tboot..."
    sleep 2
    tar -zxvf tboot-1.10.5.tar.gz
    cd tboot-1.10.5
    make all && make install || { echo "tboot build failed"; exit 1; }
    cd ..
    rm -rf tboot-1.10.5

    # GRUB
    mkdir -p /boot/efi/EFI/redhat
    cp -r /usr/lib/grub/x86_64-efi /boot/efi/EFI/redhat/
    grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg

    [ -f Change_scrip_rhel92.py ] && python3 Change_scrip_rhel92.py
    chmod +x /boot/efi/EFI/redhat/grub.cfg

    echo "Installation Complete"
fi
