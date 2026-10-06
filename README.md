# 🛠️ avathings

Central command catalog and cheat sheet for local hardware preservation and system control utilities:
- **avabatt**: [GitHub Repository](https://github.com/telosdevgroup/avabatt) · Native Linux hardware battery charge threshold manager
- **changestate**: [GitHub Repository](https://github.com/telosdevgroup/changestate) · Prime-based resource and thermal manager

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

### 🎚️ `changestate` (Compute & Thermal Governor)
Scale CPU cores, frequencies, boost states, and GPU limits dynamically using prime-indexed capacity tiers.

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
