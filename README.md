# 🛠️ avathings

Central command catalog and cheat sheet for local hardware preservation and system control utilities.

### Tool Suite
This is the complete set of tools:
- **`changestate`**: [GitHub Repository](https://github.com/telosdevgroup/changestate) · Prime-based CPU/GPU compute capacity governor (helps keep machines running cooler; BIOS manages thermals)
- **`avabatt`**: [GitHub Repository](https://github.com/telosdevgroup/avabatt) · Native Linux hardware battery charge threshold manager
- **`avathings` Applet**: Native Cinnamon taskbar applet quietly reporting on and controlling `changestate` and `avabatt`
- *...more to come!*

---

## ⚡ Quick Cheat Sheet

### 🔋 `avabatt` (Battery Lifespan Manager)
Manage native battery charge thresholds via Linux kernel sysfs interfaces without third-party daemons like TLP.

| Command | Description |
| :--- | :--- |
| `avabatt status` | Display current charge levels, limits, and hardware status |
| `avabatt status --json` | Output telemetry in JSON format |
| `sudo avabatt on` | Enable 80% charge ceiling (recommended desk limit) |
| `sudo avabatt off` | Disable conservation limit (charges up to 100%) |
| `sudo avabatt 80` | Cap charging at 80% (start threshold auto-calculated 5% lower) |
| `sudo avabatt 100` | Restore full 100% capacity (e.g. before travel) |
| `sudo avabatt 50 75` | Custom profile: start charging at 50%, stop at 75% |
| `sudo avabatt apply` | Re-apply saved thresholds from `/etc/avabatt.conf` |

#### Service & Installation
- **Install:** `curl -sSL https://raw.githubusercontent.com/telosdevgroup/avabatt/main/install.sh | bash`
- **Systemd Service:** `sudo systemctl status avabatt.service` (persists settings across boots and suspend/hibernate)

---

### 🎚️ `changestate` (Compute Capacity Governor)
Scale CPU cores, frequencies, boost states, and GPU limits dynamically using prime-indexed capacity tiers (helps keep machines running cool while leaving thermal management to the BIOS).

| Command | Description |
| :--- | :--- |
| `changestate status` | Show active capacity tier, core status, and hardware diagnostics |
| `changestate tiers-json` | Machine-tailored JSON metadata of available tiers |
| `sudo changestate p11` | Set ~35% capacity (efficient, battery sweet spot) |
| `sudo changestate p23` | Set ~75% capacity (balanced working sweet spot, boost disabled) |
| `sudo changestate p31` | Set 100% capacity (Salt Flats: fully uncapped compute and boost) |
| `sudo changestate p0` | MOM: Metal Over Moss airgap lockdown (requires typing `MOM` or passing `--confirm`) |
| `sudo changestate p<N>` | Step into any prime tier: `p2`, `p3`, `p5`, `p7`, `p11`, `p13`, `p17`, `p19`, `p23`, `p29`, `p31` |

#### Autonomous Daemon (`changestate-auto`)
Monitors activity and automatically scales capacity between `P:7` and `P:23` based on user input idle states:
- **Enable & Start:** `sudo systemctl enable --now changestate-auto`
- **Watch Live Logs:** `journalctl -u changestate-auto -f`
- **Stop Daemon:** `sudo systemctl stop changestate-auto`

---

## 🖥️ Cinnamon Panel Applet (`avathings@telosdevgroup`)

The **Avathings** native Cinnamon applet integrates both `changestate` and `avabatt` directly into your Linux Mint panel.

### Features
- **Real-Time Panel Monitoring:** Displays current tier (e.g. `P:23`), battery status, and active charge ceiling at a glance.
- **Compute Governor Control:** Quick presets (`P:11` Eco, `P:23` Balanced, `P:31` Max Uncapped), full dynamic tier flyout menu, and toggle for the `changestate-auto` autonomous daemon.
- **Battery Threshold Management:** One-click toggles for Desk Mode (80%), Full Travel (100%), and custom thresholds.
- **Non-blocking Telemetry:** Uses native asynchronous Gio subprocess calls.

### Installation & Setup

1. **Install and Enable the Applet:**
   ```bash
   ./scripts/install-applet.sh
   ./scripts/enable-applet.sh
   ```

2. **(Optional) Configure Passwordless Sudo:**
   To switch tiers and battery thresholds without a Polkit / sudo password prompt each time:
   ```bash
   sudo ./scripts/setup-sudoers.sh
   ```

---

## 📂 Repositories & Paths

- **`avabatt`**:
  - GitHub: https://github.com/telosdevgroup/avabatt
  - Local Clone: `../avabatt`
  - Binary: `/usr/local/bin/avabatt`
  - Service: `/etc/systemd/system/avabatt.service`
  - Config: `/etc/avabatt.conf`
- **`changestate` (compstate)**:
  - GitHub: https://github.com/telosdevgroup/changestate
  - Local Clone: `../compstate`
  - Binary: `/usr/local/bin/changestate`
  - Daemon Binary: `/usr/local/bin/changestate-auto`
  - Service: `/etc/systemd/system/changestate-auto.service`
- **`avathings` Applet**:
  - Source: `applet/avathings@telosdevgroup`
  - Panel UUID: `avathings@telosdevgroup`

