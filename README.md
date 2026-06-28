# Warcraft III LAN Discovery Proxy

A lightweight and efficient Python tool that enables players to discover and join Local Area Network (LAN) games in classic **Warcraft III** over Virtual Private Networks (VPNs) like **Tailscale**, **ZeroTier**, **Hamachi**, etc. on Linux.

---

## 🛠️ How It Works (Under the Hood)

Classic Warcraft III relies on UDP broadcast packets on port **6112** to announce and find active game lobbies in a local area network. Layer 3 (IP) virtual private networks (such as Tailscale) do not forward broadcast or multicast packets between connected peers by default.

This script bridges that gap using the following mechanism:

1. **Sniffing Local Requests:** Using the `scapy` library, the script sniffs your physical network interface (e.g. `eno1` or your Wi-Fi interface) to capture outgoing LAN discovery packets broadcasted by your local Warcraft III client (`W3GS_SEARCHGAME` - `0x2f` or `LanRefreshGame` - `0x32`).
2. **Tunneling the Request:** The intercepted packet (which contains your exact game client version and checksums) is cloned and forwarded directly (via UDP Unicast) to the remote host's IP address (`host_ip`) over the VPN.
3. **Receiving Details:** The remote host's Warcraft III instance receives the discovery query and replies with a unicast game details packet (`LanGameDetails` - `0x30`).
4. **L2 Broadcast Injection (Spoofing):** The script receives the reply and crafts a spoofed Layer 2 Ethernet broadcast frame containing the response, setting the source IP of the frame to the remote host's IP. Your local Warcraft III client receives this broadcast, parses the details, and displays the game in the LAN menu. When you click "Join", the game client initiates a direct TCP connection to the host's IP, which is natively routed and handled by your VPN tunnel.

---

## 📋 Prerequisites

* Operating System: **Linux**
* **Python 3** installed
* Administrator privileges (`sudo`) – required to sniff raw network interfaces and inject custom Layer 2 Ethernet frames.

---

## 🚀 Quick Start

1. **Install requirements** (using a virtual environment is highly recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install scapy
   ```

2. **Run the proxy** by specifying your friend's VPN IP address:
   ```bash
   sudo .venv/bin/python app.py <FRIEND_VPN_IP>
   ```

3. **Launch Warcraft III** and navigate to the **Local Area Network (LAN)** menu. Your friend's hosted lobby should appear in the list within a few seconds.

---

## ⚙️ CLI Usage and Options

```bash
usage: app.py [-h] [-i INTERFACE] [-l LOCAL_IP] [-p PORT] host_ip
```

| Argument | Shortcut | Default | Description |
| :--- | :--- | :--- | :--- |
| `host_ip` | — | *required* | IP address of the remote Warcraft III host (VPN IP). |
| `--interface` | `-i` | `auto` | Name of your physical network interface (e.g. `eno1`, `wlan0`). Using `auto` will automatically detect the default active interface. |
| `--local-ip` | `-l` | `0.0.0.0` | Your local IP address on the VPN interface. If set to `0.0.0.0`, the OS routing table will automatically determine the outgoing interface and source IP. |
| `--port` | `-p` | `6112` | Warcraft III game port. |

### Usage Examples:

* **Basic launch (Tailscale/ZeroTier):**
  ```bash
  sudo .venv/bin/python app.py 100.69.6.29
  ```

* **Specifying a Wi-Fi interface and local VPN interface binding:**
  ```bash
  sudo .venv/bin/python app.py 100.69.6.29 -i wlxd037454ed072 -l 100.103.35.62
  ```

---

## 🔍 W3GS Protocol Reference

The script intercepts and parses the following opcodes from the Blizzard LAN Game Protocol (W3GS):
* `0xf7` – Protocol magic byte.
* `0x2f` (`LanRequestGame`) – Discovery request broadcasted by a searching client.
* `0x32` (`LanRefreshGame`) – Discovery refresh request broadcasted by a client.
* `0x30` (`LanGameDetails`) – Response sent by the host containing game lobby details (game name, slots, map name, TCP port).
