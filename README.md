# Warcraft III LAN Discovery Proxy (wc3ts Architecture)

A lightweight and efficient Python tool that enables players to discover and join Local Area Network (LAN) games in classic **Warcraft III** (legacy) over Virtual Private Networks (VPNs) like **Tailscale**, **ZeroTier**, **Hamachi**, etc.

This script is fully cross-platform and works on **Windows**, **Linux**, and **macOS**.

## 📋 Prerequisites

- **Python 3**
- **Npcap** (Windows only) - required for packet sniffing.
- **Administrator / Root privileges** - required to sniff raw packets on physical interfaces.

---

## 🚀 Installation & Setup

### 🪟 Windows (Step-by-Step Guide)

#### Step 1: Install Python
1. Download the latest installer from the official [Python Downloads Page](https://www.python.org/downloads/).
2. Run the downloaded installer.
3. **CRITICAL:** Check the box at the bottom that says **"Add python.exe to PATH"** before clicking **Install Now**. If you skip this, the command prompt will not recognize the `python` command.

#### Step 2: Install Npcap
1. Download the installer from the [Npcap Download Page](https://npcap.com/#download).
2. Run the installer.
3. **CRITICAL:** Ensure the option **"Install Npcap in WinPcap API-compatible mode"** is checked. If it is unchecked, Scapy will not be able to capture packets.

#### Step 3: Run the Proxy
1. Save `app.py` to a folder on your computer (e.g. `C:\wc3proxy`).
2. Click the **Start Menu**, type `cmd`, right-click on **Command Prompt**, and select **Run as administrator**.
3. In the Command Prompt, navigate to your folder:
   ```cmd
   cd C:\wc3proxy
   ```
4. Install the required dependency (`scapy`):
   ```cmd
   pip install scapy
   ```
5. Start the proxy by specifying your friend's VPN IP address (e.g., if their Tailscale IP is `100.69.6.29`):
   ```cmd
   python app.py 100.69.6.29
   ```

---

### 🐧 Linux (Debian / Ubuntu / Arch / etc.)

1. Open a terminal.
2. Create a virtual environment and install Scapy:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the proxy with `sudo` (required to sniff raw packets):
   ```bash
   sudo .venv/bin/python app.py <FRIEND_VPN_IP>
   ```

---

### 🍏 macOS

1. Open a terminal.
2. Install Scapy (requires Python 3; if not present, install it via Homebrew or from Python.org):
   ```bash
   sudo pip3 install -r requirements.txt
   ```
3. Run the proxy with `sudo`:
   ```bash
   sudo python3 app.py <FRIEND_VPN_IP>
   ```

---

## 🎮 Play Instructions

1. **Host the Game:** Have your friend create a LAN game lobby in Warcraft III on their remote computer and stay in the lobby.
2. **Start the Proxy:** Run this proxy on your computer, passing your friend's VPN IP as the argument.
3. **Join the Game:** On your computer, open Warcraft III, go to **Local Area Network (LAN)**, and you should see exactly one game hosted on the list. Double-click to join and play!

---

## ⚙️ CLI Options & Configuration

```bash
usage: app.py [-h] [-i INTERFACE] [-l LOCAL_IP] [-p PORT] [--proxy-port PROXY_PORT] host_ip
```

| Argument | Shortcut | Default | Description |
| :--- | :--- | :--- | :--- |
| `host_ip` | — | *required* | IP address of the remote Warcraft III host (VPN IP). |
| `--interface` | `-i` | `auto` | Network interface (e.g. `eno1`, `wlan0`). `auto` automatically detects your active interface. |
| `--local-ip` | `-l` | `0.0.0.0` | Local IP on the VPN interface (used to bind outgoing requests). |
| `--port` | `-p` | `6112` | Warcraft III game port. |
| `--proxy-port` | — | `6115` | Local TCP port for the proxy. |

---

## 🔍 W3GS Protocol Reference

The script intercepts and modifies the following opcodes from the Blizzard LAN Game Protocol (W3GS):
* `0xf7` – Protocol signature byte.
* `0x2f` (`LanRequestGame`) – Discovery request broadcasted by a searching client.
* `0x32` (`LanRefreshGame`) – Discovery refresh request broadcasted by a client.
* `0x30` (`LanGameDetails`) – Response sent by the host containing game lobby details (game name, slots, map name, TCP port).

## Note
This is mostly AI generated. Use if you find it useful. The code is probably inspired by https://github.com/kradalby/wc3ts Copyright (c) 2025, Kristoffer Dalby. Chat didn't know how to make it work so I asked it to analyse his repo, thx. Should work everywhere. Tested on Ubuntu 24.04 LTS, fedora and win11.
