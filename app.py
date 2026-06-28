import argparse
import socket
import sys
import scapy.all as scapy

# Warcraft III Protocol Opcodes (W3GS):
# - 0xf7: W3GS protocol identifier
# - 0x2f: LanRequestGame (Search game query)
# - 0x30: LanGameDetails (Game information response)
# - 0x32: LanRefreshGame (Game refresh query)

def handle_packet(packet, local_ip, host_ip, port, interface):
    try:
        if packet.haslayer(scapy.UDP):
            payload = bytes(packet[scapy.UDP].payload)
            # Match W3GS game discovery request (0xf7 prefix with 0x2f or 0x32 opcode)
            if len(payload) > 1 and payload[0] == 0xf7 and (payload[1] == 0x2f or payload[1] == 0x32):
                print(f"[+] Intercepted local discovery request (opcode {hex(payload[1])}). Tunneling to {host_ip}:{port}...")
                
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(2.0)
                    sock.bind((local_ip, 0))
                    sock.sendto(payload, (host_ip, port))
                    
                    data, addr = sock.recvfrom(2048)
                    
                    if data and len(data) > 2 and data[0] == 0xf7 and data[1] == 0x30:
                        print(f"[+] Received game details from {addr[0]}. Injecting local LAN broadcast...")
                        
                        # Spoof the source IP in the L2 Ethernet frame to match the remote host.
                        # This forces the local Warcraft III client to connect directly to the host's IP.
                        spoofed_packet = (
                            scapy.Ether(dst="ff:ff:ff:ff:ff:ff") /
                            scapy.IP(src=host_ip, dst="255.255.255.255") /
                            scapy.UDP(sport=port, dport=port) /
                            data
                        )
                        scapy.sendp(spoofed_packet, iface=interface, verbose=False)
    except socket.timeout:
        print(f"[-] Timeout waiting for response from {host_ip}:{port}.")
    except Exception as e:
        print(f"[-] Error handling packet: {e}")

def main():
    parser = argparse.ArgumentParser(description="Warcraft III LAN Discovery Proxy")
    parser.add_argument("host_ip", help="IP address of the remote Warcraft III host")
    parser.add_argument("-i", "--interface", default="auto", 
                        help="Physical LAN network interface (e.g. eno1, wlan0) or 'auto'")
    parser.add_argument("-l", "--local-ip", default="0.0.0.0", 
                        help="Local IP of the VPN/tunnel interface (defaults to 0.0.0.0)")
    parser.add_argument("-p", "--port", type=int, default=6112, 
                        help="Warcraft III game port (default: 6112)")
    
    args = parser.parse_args()
    
    interface = args.interface
    if interface == "auto":
        try:
            interface = scapy.get_working_if().name
            print(f"[*] Auto-detected active LAN interface: {interface}")
        except Exception as e:
            print(f"[-] Interface auto-detection failed: {e}")
            print("[!] Please specify network interface manually using -i flag")
            sys.exit(1)
            
    print(f"[*] Proxy running on interface '{interface}' targeting host {args.host_ip}:{args.port}")
    print("[*] Open the LAN game menu in Warcraft III to trigger discovery...")
    
    try:
        scapy.sniff(
            iface=interface, 
            filter=f"udp and port {args.port}", 
            prn=lambda pkt: handle_packet(pkt, args.local_ip, args.host_ip, args.port, interface), 
            store=0
        )
    except KeyboardInterrupt:
        print("\n[*] Proxy stopped.")
    except Exception as e:
        print(f"[-] Sniffer error: {e}")

if __name__ == "__main__":
    main()
