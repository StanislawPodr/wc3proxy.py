import argparse
import socket
import sys
import threading
import scapy.all as scapy

# Warcraft III Protocol Opcodes (W3GS):
# - 0xf7: W3GS protocol identifier
# - 0x2f: LanRequestGame (Search game query)
# - 0x30: LanGameDetails (Game information response)
# - 0x32: LanRefreshGame (Game refresh query)

def get_active_interfaces():
    active_interfaces = []
    try:
        import os
        is_windows = os.name == "nt"
        for iface_name, iface in scapy.conf.ifaces.items():
            name_lower = iface.name.lower()
            
            # Skip loopback
            if "loopback" in name_lower or "software loopback" in name_lower:
                continue
                
            # On Linux/macOS, check if interface is UP and RUNNING
            if not is_windows:
                flags_str = str(iface.flags).upper()
                if "UP" not in flags_str or ("RUNNING" not in flags_str and "LOWER_UP" not in flags_str):
                    continue
                
            # Skip virtual/VPN interfaces with zero MAC (like tailscale0, tun0)
            if not iface.mac or iface.mac == "00:00:00:00:00:00":
                continue
                
            # Skip interfaces without a configured IP
            if not iface.ip or iface.ip == "0.0.0.0":
                continue
                
            # Skip Docker, bridge, and libvirt/virtual interfaces by name pattern
            if any(p in name_lower for p in ["docker", "br-", "virbr", "vboxnet", "veth", "virtual", "pseudo"]):
                continue
                
            active_interfaces.append(iface.name)
    except Exception as e:
        print(f"[-] Error scanning interfaces: {e}")
    return active_interfaces

def handle_packet(packet, local_ip, host_ip, port, interface, proxy_port):
    try:
        if packet.haslayer(scapy.UDP) and packet.haslayer(scapy.IP):
            # Ignore unicast traffic to/from the host IP to prevent routing loops
            if packet[scapy.IP].dst == host_ip or packet[scapy.IP].src == host_ip:
                return

            payload = bytes(packet[scapy.UDP].payload)
            # Match W3GS game discovery request (0xf7 prefix with 0x2f or 0x32 opcode)
            if len(payload) > 1 and payload[0] == 0xf7 and (payload[1] == 0x2f or payload[1] == 0x32):
                print(f"[+] Intercepted local discovery request (opcode {hex(payload[1])}) on {interface}. Tunneling to {host_ip}:{port}...")
                
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(2.0)
                    sock.bind((local_ip, 0))
                    sock.sendto(payload, (host_ip, port))
                    
                    data, addr = sock.recvfrom(2048)
                    
                    if data and len(data) > 2 and data[0] == 0xf7 and data[1] == 0x30:
                        print(f"[+] Received game details from {addr[0]}. Modifying port to {proxy_port}...")
                        
                        # Copy data to bytearray to modify it
                        data_list = bytearray(data)
                        
                        # The port field in LanGameDetails is the last 2 bytes of the payload (little-endian uint16)
                        if len(data_list) >= 6:
                            port_idx = len(data_list) - 2
                            data_list[port_idx] = proxy_port & 0xff
                            data_list[port_idx+1] = (proxy_port >> 8) & 0xff
                        
                        # Send game details to local 
                        try:
                            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as usock:
                                usock.sendto(data_list, (local_ip, port))
                        except Exception as e:
                            print(f"[-] Error sending game details: {e}")
    except socket.timeout:
        # Ignore timeouts silently as they are expected when host has no active game lobby
        pass
    except Exception as e:
        print(f"[-] Error handling packet on {interface}: {e}")

def run_tcp_proxy(local_ip, host_ip, port, proxy_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((local_ip, proxy_port))
        server.listen(10)
        print(f"[*] TCP Proxy listening on {local_ip}:{proxy_port} (tunneling to {host_ip}:{port})")
    except Exception as e:
        print(f"[-] TCP Proxy failed to bind to {local_ip}:{proxy_port}: {e}")
        return
        
    while True:
        try:
            client_sock, addr = server.accept()
            print(f"[+] TCP Proxy: Connection from local client {addr[0]}:{addr[1]}")
            threading.Thread(target=handle_tcp_connection, args=(client_sock, host_ip, port), daemon=True).start()
        except Exception:
            break

def handle_tcp_connection(client_sock, host_ip, port):
    try:
        remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_sock.connect((host_ip, port))
        print(f"[+] TCP Proxy: Connected to remote host {host_ip}:{port}")
        
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
                print("[*] TCP Proxy connection closed.")
            except Exception:
                pass
            finally:
                src.close()
                dst.close()
                
        threading.Thread(target=forward, args=(client_sock, remote_sock), daemon=True).start()
        threading.Thread(target=forward, args=(remote_sock, client_sock), daemon=True).start()
    except Exception as e:
        print(f"[-] TCP Proxy connection failed: {e}")
        client_sock.close()

def main():
    parser = argparse.ArgumentParser(description="Warcraft III LAN Discovery Proxy (wc3ts Architecture)")
    parser.add_argument("host_ip", help="IP address of the remote Warcraft III host")
    parser.add_argument("-i", "--interface", default="auto", 
                        help="Physical LAN network interface (e.g. eno1, wlan0), comma-separated list, or 'auto'")
    parser.add_argument("-l", "--local-ip", default="0.0.0.0", 
                        help="Local IP of the VPN/tunnel interface (defaults to 0.0.0.0)")
    parser.add_argument("-p", "--port", type=int, default=6112, 
                        help="Warcraft III game port (default: 6112)")
    parser.add_argument("--proxy-port", type=int, default=6115, 
                        help="Local TCP proxy port (default: 6115)")
    
    args = parser.parse_args()
    
    interfaces = []
    if args.interface == "auto":
        active = get_active_interfaces()
        if active:
            interfaces = active
            print(f"[*] Auto-detected active LAN interface(s): {', '.join(interfaces)}")
        else:
            try:
                fallback = scapy.get_working_if().name
                interfaces = [fallback]
                print(f"[!] No active physical interfaces detected. Falling back to: {fallback}")
            except Exception as e:
                print(f"[-] Interface auto-detection failed: {e}")
                print("[!] Please specify network interface manually using -i flag")
                sys.exit(1)
    else:
        interfaces = [i.strip() for i in args.interface.split(",") if i.strip()]
        
    print(f"[*] Proxy running on interface(s): {', '.join(interfaces)} targeting host {args.host_ip}:{args.port}")
    
    # Start TCP proxy thread
    tcp_thread = threading.Thread(
        target=run_tcp_proxy,
        args=(args.local_ip, args.host_ip, args.port, args.proxy_port),
        daemon=True
    )
    tcp_thread.start()
    
    print("[*] Open the LAN game menu in Warcraft III to trigger discovery...")
    
    def run_sniffer(iface):
        try:
            scapy.sniff(
                iface=iface,
                filter=f"udp and port {args.port}",
                prn=lambda pkt: threading.Thread(
                    target=handle_packet,
                    args=(pkt, args.local_ip, args.host_ip, args.port, iface, args.proxy_port),
                    daemon=True
                ).start(),
                store=0
            )
        except Exception as e:
            print(f"[-] Sniffer error on interface '{iface}': {e}")
            
    sniff_threads = []
    for iface in interfaces:
        t = threading.Thread(target=run_sniffer, args=(iface,), daemon=True)
        t.start()
        sniff_threads.append(t)
        
    try:
        while True:
            for t in sniff_threads:
                t.join(timeout=1.0)
    except KeyboardInterrupt:
        print("\n[*] Proxy stopped.")

if __name__ == "__main__":
    main()
