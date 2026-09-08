#!/usr/bin/env bash
set -e

# 1. Configure Static IP on eth0 via NetworkManager
sudo nmcli connection delete direct-tether 2>/dev/null || true
sudo nmcli connection add type ethernet con-name direct-tether ifname eth0 ip4 192.168.123.1/24

# 2. Install and configure dnsmasq for DHCP leases
sudo apt-get update
sudo apt-get install -y dnsmasq

cat <<EOF | sudo tee /etc/dnsmasq.conf
interface=eth0
dhcp-range=192.168.123.10,192.168.123.50,255.255.255.0,12h
EOF

# 3. Enable and restart services
sudo systemctl restart NetworkManager
sudo systemctl enable --now dnsmasq

echo "Direct Ethernet tether configured. Pi IP: 192.168.123.1"