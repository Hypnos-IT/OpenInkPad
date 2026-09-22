# OpenInkPad

[![Get Latest Release](https://img.shields.io/badge/Get_Latest_Release-Download_ZIP-2ea44f?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Hypnos-IT/OpenInkPad/releases/latest)

[![License: EUPL 1.2](https://img.shields.io/badge/License-EUPL%201.2-blue.svg)](LICENSE)
[![Python: 3.x](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Latest Release](https://img.shields.io/github/v/release/Hypnos-IT/OpenInkPad?color=blue&label=Latest%20Release)](https://github.com/Hypnos-IT/OpenInkPad/releases/latest)

[Wersja polska (Polish version)](README.pl.md)

OpenInkPad is a standalone Python 3 tool to read, back up, reset, and restore the waste ink pad counter on over 1,270 Epson printer models, including the L386, L3150, EcoTank ET, XP, WF, Stylus, and Artisan series.

Written in standard Python without external dependencies.

The tool includes a step-by-step terminal wizard, an automatic network scanner that discovers Wi-Fi printers on your subnet, a background process cleaner for interfering Epson services, and direct USB support on Windows through Win32 APIs.

---

### Why this project exists

This started when my mother's Epson printer suddenly locked up because of an internal waste ink counter limit.

Printers should not stop working just because a software counter tripped, especially when commercial unlock utilities charge $10 or more for a single reset key. I wrote this tool as an open-source utility to let owners and repair shops reset the counter themselves.

---

## Support me

[![GitHub Sponsors](https://img.shields.io/badge/GitHub_Sponsors-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Hypnos-IT)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/hypnosit)

---

## Interactive wizard mode (recommended)

Run the script in PowerShell or CMD as Administrator:

```powershell
python .\openinkpad.py
```

Running as Administrator allows the script to stop background Epson services and talk directly over USB.

The wizard walks you through:
1. Choosing your language (English or Polish).
2. Closing Epson background tasks that might block the port (such as `epsonscansvc` or `Epson Status Monitor`).
3. Selecting a connection: automatic network scan, manual IP address, direct USB, or Windows Print Spooler.
4. Detecting or picking your printer model from the 1,270+ model database.
5. Reading the counter, saving an EEPROM backup, resetting to 0%, or restoring a past backup.

---

## Background tasks and prerequisites

Epson monitoring utilities continuously query the printer, which can lock the communication port.

The interactive wizard can close these for you. If you prefer to stop them manually:

### 1. Stop the scan service (epsonscansvc)
In PowerShell as Administrator:
```powershell
Stop-Service -Name "epsonscansvc" -Force -ErrorAction SilentlyContinue
```
Or in CMD:
```cmd
net stop epsonscansvc
```

### 2. Close background monitoring processes
In PowerShell:
```powershell
Get-Process *epson*, *seiko* -ErrorAction SilentlyContinue | Stop-Process -Force
```
You can also close processes like `Epson Status Monitor` or `E_IATIA01.EXE` in Windows Task Manager (Ctrl + Shift + Esc).

---

## Command line interface (CLI mode)

You can also pass arguments directly for scripts or automation.

### Network / Wi-Fi (recommended)

```powershell
# Auto-scan local network and read status
python .\openinkpad.py --scan read

# Read counter status from a specific IP
python .\openinkpad.py --host 192.168.1.67 read

# Save EEPROM registers to a backup file
python .\openinkpad.py --host 192.168.1.67 backup

# Reset waste ink counters to 0%
python .\openinkpad.py --host 192.168.1.67 reset

# Restore EEPROM registers from backup
python .\openinkpad.py --host 192.168.1.67 restore
```

### Direct USB cable (Windows)

Open PowerShell or CMD as Administrator:

```powershell
python .\openinkpad.py --usb read
python .\openinkpad.py --usb reset
```

---

## CLI options and flags

| Option | Value | Description |
|---|---|---|
| `--scan` | None | Scan local network for Epson printers (SNMP UDP port 161). |
| `--host` | `<IP>` | Printer IP address over Wi-Fi or Ethernet. |
| `--usb` | None | Direct USB connection on Windows via Win32 SetupAPI. Needs Administrator console. |
| `--model` | `<NAME>` | Printer model name (such as `L386`, `L3150`, `ET-2700`, `XP-2100`). |
| `--list-models` | `[query]` | List or search supported models in `prn_models.py`. |
| `--backup-file` | `<path>` | Custom file path for EEPROM backup. |
| `--spooler` | `"<Name>"` | Fallback connection through Windows Print Spooler. |
| `--lang` | `en` / `pl` | Output language (`en` default, `pl` for Polish). |

---

## Supported models

The `prn_models.py` file includes profiles for over 1,270 models:

```powershell
# List all models
python .\openinkpad.py --list-models

# Filter by series
python .\openinkpad.py --list-models L3
python .\openinkpad.py --list-models ET-
python .\openinkpad.py --list-models XP
```

---

## Reset procedure and device restart

1. Check current values with `read`. If the main counter reached 100%, the printer locks down.
2. Run `reset` and confirm with `yes`. The script creates a backup before writing new values.
3. Turn off the printer with its power button.
4. Wait 10 seconds, then turn it back on. The printer reloads the zeroed EEPROM values and resumes normal operation.

---

## Physical maintenance (waste ink pads)

Resetting the software clears the counter in memory, but does not empty the ink pad.

Before printing heavily again:
* Take out the waste ink box at the back of the printer, rinse the pads under water and let them dry completely (or swap them for fresh pads), or
* Reroute the internal drain tube to an external waste bottle.

---

## Acknowledgements and references

This project relies on protocol research and data published by the open-source community:

* **[epson_print_conf](https://github.com/Ircama/epson_print_conf)** by **Ircama**: research on Epson ESC/I protocol, SNMP UDP OID tunneling, and EEPROM layout.
* **[ReInkPy](https://codeberg.org/atufi/reinkpy/)** by **atufi**: database of EEPROM register addresses, reset keys, and counter formulas.
* **[epson-waste-reset](https://github.com/MAkcanca/epson-waste-reset)** by **MAkcanca**: compilation and packaging of the 1,270+ model database in `prn_models.py`.

---

## Disclaimer and safety notice

This tool writes directly to printer EEPROM registers. You use it at your own risk.

Keep two practical risks in mind:
* Ink leakage: the reset is purely digital. If you do not clean or replace the saturated pads, waste ink will eventually overflow and risk damaging electronics or surfaces.
* Interrupted writes: do not unplug cables or power off the printer while registers are being written. The tool saves an automatic backup before writing so you can restore if needed.

The author assumes no liability for hardware damage, spilled ink, or lost data.

---

## License and author

**Author:** [Hypnos-IT](https://github.com/Hypnos-IT)  
**Contact:** admin@hypnos-it.eu  
**License:** [EUPL-1.2](LICENSE)

Distributed under the **European Union Public Licence v1.2 (EUPL-1.2)**.

* Users and repair shops may use this tool freely for personal or commercial repairs.
* The EUPL is a copyleft license. Any derivative works, modifications, or network services based on this code must stay open source under the EUPL or a compatible license.
* Under Article 15 of the EUPL, this license is governed by the law of the European Union Member State of the licensor.

See [LICENSE](LICENSE) for the full license text.
