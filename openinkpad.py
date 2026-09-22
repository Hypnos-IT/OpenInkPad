#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenInkPad
Universal, dependency-free tool to read, backup, reset, and restore Waste Ink Pad
Counters for 1270+ Epson printer models (L386, L3150, ET, XP, WF series).

Author: Hypnos-IT (https://github.com/Hypnos-IT) | Contact: admin@hypnos-it.eu
License: EUPL-1.2

Based on open-source reverse engineering research:
- epson_print_conf by Ircama (ESC/I protocol & SNMP UDP OID tunneling)
- ReInkPy by atufi (EEPROM registers & model profiles)
- Model database consolidation by MAkcanca (epson-waste-reset)

Features:
- Interactive wizard menu when run with no arguments
- Automatic network discovery of Epson printers (SNMP UDP port 161)
- Automatic detection and termination of interfering background Epson processes & services
- Direct USB communication on Windows (Win32 SetupAPI / Direct I/O, no libusb required)
- Windows Print Spooler support (fallback mode)
- Dual language support (English / Polski)
"""

import sys
import time
import socket
import struct
import re
import argparse
import subprocess

# ==============================================================================
# Model database (prn_models.py) and emergency fallback for L386
# ==============================================================================
FALLBACK_MODELS = {
    "L386": {
        "read_key": [16, 8],
        "write_key": b"Sinabung",
        "reset": {
            24: 0, 25: 0, 30: 0, 28: 0, 29: 0, 46: 94,
            26: 0, 27: 0, 34: 0, 47: 94, 49: 0
        },
        "counters": [
            ["main_waste", [24, 25, 30], 62.07],
            ["borderless_waste", [26, 27, 34], 24.2]
        ],
    }
}

try:
    from prn_models import MODELS
except ImportError:
    MODELS = FALLBACK_MODELS

OID_PREFIX = "1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1"
MODEL_NAME_OID = "1.3.6.1.4.1.1248.1.1.3.1.3.8.0"

# ==============================================================================
# Internationalization / Wielojęzyczność (EN / PL)
# ==============================================================================
CURRENT_LANG = "en"

STRINGS = {
    "en": {
        "app_title": "OpenInkPad",
        "author_info": "Author: Hypnos-IT (https://github.com/Hypnos-IT) | Contact: admin@hypnos-it.eu",
        "license_info": "License: EUPL-1.2",
        "lang_select_prompt": "Select language / Wybierz jezyk [1: English (default), 2: Polski]: ",
        "lang_switched": "Language switched to English.",
        
        # Background tasks
        "bg_checking": "Checking background Epson processes and services...",
        "bg_clean": "No interfering Epson processes or services detected.",
        "bg_detected_title": "Epson background tasks detected",
        "bg_service_item": "System service: epsonscansvc (Running)",
        "bg_process_item": "Background processes ({count}): {list}",
        "bg_warning": "These tasks can lock USB/network ports and block service commands.",
        "bg_admin_hint": "Tip: Console is not running as Administrator. Stopping system services or opening direct USB may require elevated privileges.",
        "bg_prompt_kill": "Do you want to terminate these processes and stop the service now? [Y/n]: ",
        "bg_stopping_svc": "Stopping service epsonscansvc...",
        "bg_svc_ok": "OK",
        "bg_svc_fail": "Failed (administrator privileges required)",
        "bg_killed": "Terminated processes: {list}",
        "bg_kill_failed": "Could not terminate: {list} (run console as Administrator)",
        "bg_done": "Background tasks management completed.",
        
        # Connection menu
        "conn_title": "Select connection method:",
        "conn_opt_scan": "[1] Auto-scan local network for Epson printers (Recommended)",
        "conn_opt_wifi": "[2] Wi-Fi / Local Network (Enter IP manually)",
        "conn_opt_usb": "[3] Direct USB Cable (Win32 Direct I/O)",
        "conn_opt_spooler": "[4] Windows Print Spooler",
        "conn_opt_exit": "[0] Exit program",
        "conn_prompt": "Choose option [0-4] (default 1): ",
        "conn_scan_start": "Scanning local network for Epson printers (SNMP UDP port 161)...",
        "conn_scan_none": "No Epson printers found on local network.",
        "conn_scan_hint": "Ensure the printer is powered on and connected to Wi-Fi, or enter its IP manually (option 2).",
        "conn_scan_found": "Found Epson printer: {model} at {ip}",
        "conn_scan_confirm": "Connect to this printer? [Y/n]: ",
        "conn_scan_multi": "Found {count} Epson printers on the network:",
        "conn_scan_select": "Select printer [1-{count}]: ",
        "conn_wifi_ip_prompt": "Enter printer IP address: ",
        "conn_wifi_ip_empty": "IP address cannot be empty. Please enter a valid IP address.",
        "conn_wifi_connecting": "Connecting to printer at {ip}...",
        "conn_wifi_response": "Connected to device: {name}",
        "conn_wifi_error": "Connection failed: No response from printer at {ip} ({err}).",
        "conn_wifi_hint": "Check if the printer is powered on and reachable on your network.",
        "conn_usb_connecting": "Connecting directly via USB...",
        "conn_usb_found": "Found USB device: {path}",
        "conn_usb_error": "USB error: {err}",
        "conn_spooler_prompt": "Enter Windows printer name (default 'EPSON L386 Series'): ",
        "conn_exit": "Program terminated.",
        
        # Model selection
        "model_auto_detected": "Automatically detected model: {model}",
        "model_use_detected": "Use this model profile? [Y/n]: ",
        "model_menu_title": "Select printer model:",
        "model_opt_default": "[1] Epson L386 (and L380 / L382 / L385) - Default",
        "model_opt_custom": "[2] Enter model name (e.g. L3150, ET-2700, XP-2100)",
        "model_opt_search": "[3] Search database of 1270+ models",
        "model_prompt": "Choose option [1-3] (default 1): ",
        "model_enter_name": "Enter model name: ",
        "model_not_found": "Model '{name}' was not found in the database.",
        "model_search_query": "Enter search term (or press Enter for full list): ",
        "model_active": "Active model profile: {model}",
        
        # Main Action Menu
        "menu_header": "OpenInkPad | Model: {model} | Connection: {conn}",
        "menu_opt_1": "[1] Read waste ink counters (Read)",
        "menu_opt_2": "[2] Backup EEPROM to file (Backup)",
        "menu_opt_3": "[3] Reset waste ink counters to 0% (Reset)",
        "menu_opt_4": "[4] Restore EEPROM from backup file (Restore)",
        "menu_opt_5": "[5] Check & terminate background Epson tasks",
        "menu_opt_6": "[6] Change printer model",
        "menu_opt_7": "[7] Switch language / Zmien jezyk (EN/PL)",
        "menu_opt_0": "[0] Exit program",
        "menu_prompt": "Choose operation [0-7]: ",
        
        # Operations
        "status_title": "WASTE INK COUNTER STATUS - {model}",
        "status_no_counters": "Notice: No counter definitions in this model profile.",
        "status_available_map": "Available reset map: {count} EEPROM addresses.",
        "status_locked": "[LOCKED / FULL!]",
        "status_normal": "[Normal]",
        "status_warning": "[Attention needed]",
        "status_points": "points",
        
        "backup_creating": "Creating EEPROM backup -> '{path}' ...",
        "backup_success": "EEPROM backup ({count} registers) saved to: {path}",
        
        "reset_warning": "Warning: You are about to reset the waste ink pad counter for model {model}.",
        "reset_confirm": "Are you sure you want to reset counters to 0%? [yes/no]: ",
        "reset_cancelled": "Operation cancelled by user.",
        "reset_starting": "Writing zeroed values to EEPROM registers...",
        "reset_success_title": "[OK] Waste ink counters reset to 0%.",
        "reset_steps_title": "Next steps:",
        "reset_step_1": "1. Turn off the printer with the power button.",
        "reset_step_2": "2. Wait 10 seconds and turn it back on.",
        "reset_step_3": "The printer will restart with cleared counters and be ready to print.",
        
        "restore_loading": "Loading EEPROM backup from file: '{path}' ...",
        "restore_not_found": "Backup file '{path}' was not found!",
        "restore_invalid": "File '{path}' does not contain valid EEPROM memory entries.",
        "restore_found_entries": "Found {count} EEPROM registers to restore.",
        "restore_confirm": "Are you sure you want to restore EEPROM from '{path}'? [yes/no]: ",
        "restore_success": "[OK] EEPROM registers restored from backup.",
        
        "op_error": "Error during operation: {err}",
        "invalid_choice": "Invalid selection. Please enter a valid number.",
        
        # CLI
        "cli_desc": "OpenInkPad - Universal service tool for 1270+ Epson printer models (Pure Python 3, ZERO pip).",
        "cli_err_conn": "Error: Specify connection method: --scan, --host <IP>, --usb or --spooler <Name> (or run with no arguments for interactive menu).",
        "cli_model_not_found": "Error: Model '{name}' not found in database.",
        "cli_model_list_hint": "Run 'python openinkpad.py --list-models' to browse the database.",
        "cli_default_profile": "Using default profile: Epson L386 (use --model to specify another).",
    },
    "pl": {
        "app_title": "OpenInkPad",
        "author_info": "Autor: Hypnos-IT (https://github.com/Hypnos-IT) | Kontakt: admin@hypnos-it.eu",
        "license_info": "Licencja: EUPL-1.2",
        "lang_select_prompt": "Wybierz jezyk / Select language [1: English, 2: Polski]: ",
        "lang_switched": "Przelaczono jezyk na polski.",
        
        # Zadania w tle
        "bg_checking": "Sprawdzanie procesow i uslug Epsona w tle...",
        "bg_clean": "Nie wykryto kolidujacych procesow ani uslug Epsona w tle.",
        "bg_detected_title": "Wykryto aktywne programy lub uslugi Epsona w tle",
        "bg_service_item": "Usluga systemowa: epsonscansvc (Uruchomiona)",
        "bg_process_item": "Procesy w tle ({count}): {list}",
        "bg_warning": "Moga one blokowac port USB/sieciowy i uniemozliwiac komunikacje serwisowa.",
        "bg_admin_hint": "Wskazowka: Konsola nie jest uruchomiona jako Administrator. Zatrzymanie uslugi epsonscansvc lub tryb USB Direct moga wymagac uprawnien administratora.",
        "bg_prompt_kill": "Czy chcesz zamknac te procesy i zatrzymac usluge teraz? [T/n]: ",
        "bg_stopping_svc": "Zatrzymywanie uslugi epsonscansvc...",
        "bg_svc_ok": "OK",
        "bg_svc_fail": "Nie powiodlo sie (wymagane uprawnienia administratora)",
        "bg_killed": "Zamknieto procesy: {list}",
        "bg_kill_failed": "Nie udalo sie zamknac: {list} (uruchom konsole jako Administrator)",
        "bg_done": "Zakonczono zarzadzanie procesami w tle.",
        
        # Menu połączenia
        "conn_title": "Wybierz sposob polaczenia z drukarka:",
        "conn_opt_scan": "[1] Automatyczne wyszukiwanie w sieci (Skanowanie LAN) - Zalecane",
        "conn_opt_wifi": "[2] Wi-Fi / Siec lokalna (Podaj adres IP recznie)",
        "conn_opt_usb": "[3] Bezposredni kabel USB (Win32 Direct I/O)",
        "conn_opt_spooler": "[4] Bufor wydruku Windows Spooler",
        "conn_opt_exit": "[0] Zakoncz program",
        "conn_prompt": "Wybierz opcje [0-4] (domyslnie 1): ",
        "conn_scan_start": "Skanowanie lokalnej sieci w poszukiwaniu drukarek Epson (SNMP UDP 161)...",
        "conn_scan_none": "Nie znaleziono drukarek Epson w lokalnej sieci.",
        "conn_scan_hint": "Upewnij sie, ze drukarka jest wlaczona i w tej samej sieci Wi-Fi, lub wybierz opcje [2] i wpisz IP.",
        "conn_scan_found": "Znaleziono drukarke Epson: {model} pod adresem {ip}",
        "conn_scan_confirm": "Czy polaczyc sie z tym urzadzeniem? [T/n]: ",
        "conn_scan_multi": "Znaleziono {count} drukarki Epson w sieci:",
        "conn_scan_select": "Wybierz drukarke [1-{count}]: ",
        "conn_wifi_ip_prompt": "Podaj adres IP drukarki: ",
        "conn_wifi_ip_empty": "Adres IP nie moze byc pusty. Wpisz poprawny adres (np. 192.168.1.67).",
        "conn_wifi_connecting": "Laczenie z drukarka pod adresem {ip}...",
        "conn_wifi_response": "Polaczono z urzadzeniem: {name}",
        "conn_wifi_error": "Blad polaczenia: Brak odpowiedzi od drukarki pod adresem {ip} ({err}).",
        "conn_wifi_hint": "Upewnij sie, ze drukarka jest wlaczona i osiagalna w Twojej sieci Wi-Fi.",
        "conn_usb_connecting": "Laczenie bezposrednio przez USB...",
        "conn_usb_found": "Znaleziono urzadzenie USB: {path}",
        "conn_usb_error": "Blad USB: {err}",
        "conn_spooler_prompt": "Podaj nazwe drukarki w Windows (domyslnie 'EPSON L386 Series'): ",
        "conn_exit": "Zakonczono program.",
        
        # Wybór modelu
        "model_auto_detected": "Automatycznie rozpoznano model: {model}",
        "model_use_detected": "Czy uzyc tego profilu? [T/n]: ",
        "model_menu_title": "Wybierz model drukarki:",
        "model_opt_default": "[1] Epson L386 (oraz L380 / L382 / L385) - Domyslny",
        "model_opt_custom": "[2] Wpisz inny model (np. L3150, ET-2700, XP-2100)",
        "model_opt_search": "[3] Przeszukaj baze ponad 1270 modeli",
        "model_prompt": "Wybierz opcje [1-3] (domyslnie 1): ",
        "model_enter_name": "Podaj nazwe modelu: ",
        "model_not_found": "Nie znaleziono modelu '{name}' w bazie.",
        "model_search_query": "Wpisz fragment nazwy (lub Enter dla calej listy): ",
        "model_active": "Aktywny profil modelu: {model}",
        
        # Menu główne operacji
        "menu_header": "OpenInkPad | Model: {model} | Polaczenie: {conn}",
        "menu_opt_1": "[1] Odczytaj stan licznikow (Read)",
        "menu_opt_2": "[2] Wykonaj kopie zapasowa EEPROM (Backup)",
        "menu_opt_3": "[3] Zresetuj liczniki pampersa do 0% (Reset)",
        "menu_opt_4": "[4] Przywroc stan z kopii zapasowej (Restore)",
        "menu_opt_5": "[5] Sprawdz i zamknij procesy Epsona w tle",
        "menu_opt_6": "[6] Zmien model drukarki",
        "menu_opt_7": "[7] Switch language / Zmien jezyk (EN/PL)",
        "menu_opt_0": "[0] Zakoncz program (Exit)",
        "menu_prompt": "Wybierz operacje [0-7]: ",
        
        # Operacje
        "status_title": "STAN LICZNIKOW ZUZYCIA - {model}",
        "status_no_counters": "Uwaga: Brak definicji licznikow w profilu tego modelu.",
        "status_available_map": "Dostepna mapa resetu: {count} adresow EEPROM.",
        "status_locked": "[ZABLOKOWANA!]",
        "status_normal": "[W normie]",
        "status_warning": "[Wymaga uwagi]",
        "status_points": "punkty",
        
        "backup_creating": "Tworzenie kopii zapasowej EEPROM -> '{path}' ...",
        "backup_success": "Kopia zapasowa EEPROM ({count} rejestrow) zapisana do: {path}",
        
        "reset_warning": "Uwaga: Resetujesz licznik pampersa dla modelu {model}.",
        "reset_confirm": "Czy na pewno chcesz zresetowac licznik do 0%? [tak/nie]: ",
        "reset_cancelled": "Operacja anulowana przez uzytkownika.",
        "reset_starting": "Rozpoczynanie zerowania komorek EEPROM...",
        "reset_success_title": "[OK] Liczniki pampersa zostaly wyzerowane (0%).",
        "reset_steps_title": "Nastepny krok:",
        "reset_step_1": "1. Wylacz drukarke przyciskiem zasilania.",
        "reset_step_2": "2. Odczekaj 10 sekund i wlacz ja ponownie.",
        "reset_step_3": "Drukarka uruchomi sie juz bez bledu i bedzie gotowa do pracy.",
        
        "restore_loading": "Wczytywanie kopii zapasowej EEPROM z pliku: '{path}' ...",
        "restore_not_found": "Plik kopii zapasowej '{path}' nie zostal znaleziony!",
        "restore_invalid": "Plik '{path}' nie zawiera prawidlowych wpisow rejestrow EEPROM.",
        "restore_found_entries": "Znaleziono {count} rejestrow do przywrocenia.",
        "restore_confirm": "Czy na pewno chcesz przywrocic EEPROM z pliku '{path}'? [tak/nie]: ",
        "restore_success": "[OK] Zawartosc pamieci EEPROM zostala przywrocona z kopii.",
        
        "op_error": "Blad podczas operacji: {err}",
        "invalid_choice": "Nieprawidlowy wybor, wpisz wlasciwa cyfre.",
        
        # CLI
        "cli_desc": "OpenInkPad - Uniwersalne narzedzie serwisowe dla ponad 1270 modeli drukarek Epson (100% Czysty Python, ZERO pip).",
        "cli_err_conn": "Blad: Podaj sposob polaczenia: --scan, --host <IP>, --usb lub --spooler <Nazwa> (lub uruchom bez parametrow dla menu).",
        "cli_model_not_found": "Blad: Nie znaleziono w bazie modelu '{name}'.",
        "cli_model_list_hint": "Wpisz 'python openinkpad.py --list-models' aby przeszukac baze.",
        "cli_default_profile": "Uzyto domyslnego profilu: Epson L386 (uzyj --model, aby wskazac inny).",
    }
}


def t(key, **kwargs):
    """Pobiera przetłumaczony ciąg znaków dla bieżącego języka."""
    lang_dict = STRINGS.get(CURRENT_LANG, STRINGS["en"])
    text = lang_dict.get(key, STRINGS["en"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def set_language(lang):
    global CURRENT_LANG
    if lang in ("pl", "polski", "2"):
        CURRENT_LANG = "pl"
    else:
        CURRENT_LANG = "en"


def normalize_model_name(name):
    """Normalizuje nazwę modelu do porównywania."""
    return re.sub(r"\b(epson|series)\b", "", name, flags=re.I).replace(" ", "").replace("-", "").upper()


def resolve_model(name):
    """Dopasowuje nazwę modelu do bazy MODELS. Zwraca (oficjalna_nazwa, profil_modelu)."""
    if not name:
        return None, None
    if name in MODELS:
        return name, MODELS[name]

    norm = normalize_model_name(name)
    norm_map = {normalize_model_name(k): k for k in MODELS}
    if norm in norm_map:
        key = norm_map[norm]
        return key, MODELS[key]

    for k_norm, orig_key in norm_map.items():
        if norm and (k_norm.startswith(norm) or norm.startswith(k_norm)):
            return orig_key, MODELS[orig_key]

    return None, None


def list_supported_models(query=None):
    """Wyświetla listę obsługiwanych modeli drukarek."""
    keys = sorted(MODELS.keys())
    if query:
        q_norm = normalize_model_name(query)
        keys = [k for k in keys if q_norm in normalize_model_name(k)]
        if CURRENT_LANG == "pl":
            print(f"\nZnaleziono {len(keys)} modeli pasujacych do '{query}':")
        else:
            print(f"\nFound {len(keys)} models matching '{query}':")
    else:
        if CURRENT_LANG == "pl":
            print(f"\nBaza zawiera {len(keys)} obslugiwanych modeli drukarek Epson:")
        else:
            print(f"\nDatabase contains {len(keys)} supported Epson printer models:")

    col_width = 20
    cols = 4
    for i in range(0, len(keys), cols):
        chunk = keys[i:i + cols]
        print("  " + "".join(f"{k:<{col_width}}" for k in chunk))
    if CURRENT_LANG == "pl":
        print(f"\nLacznie: {len(keys)} modeli.")
        print("Uzycie CLI: python openinkpad.py --model <NAZWA> --host <IP> read\n")
    else:
        print(f"\nTotal: {len(keys)} models.")
        print("CLI usage: python openinkpad.py --model <NAME> --host <IP> read\n")


# ==============================================================================
# Zarządzanie procesami i usługami w tle
# ==============================================================================
def find_epson_tasks():
    """Zwraca listę aktywnych procesów powiązanych z Epsonem."""
    if not sys.platform.startswith("win"):
        return []
    procs = []
    try:
        res = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="ignore")
        for line in res.stdout.splitlines():
            line = line.strip()
            if line:
                parts = [p.strip('"') for p in line.split('","')]
                if parts:
                    name = parts[0]
                    low = name.lower()
                    if any(k in low for k in ["epson", "seiko", "e_ia", "e_fa", "status monitor"]):
                        procs.append(name)
    except Exception:
        pass
    return list(set(procs))


def is_epson_service_running():
    """Sprawdza, czy usługa epsonscansvc jest uruchomiona."""
    if not sys.platform.startswith("win"):
        return False
    try:
        res = subprocess.run(["sc", "query", "epsonscansvc"], capture_output=True, text=True, errors="ignore")
        return "RUNNING" in res.stdout.upper()
    except Exception:
        return False


def stop_epson_service():
    """Zatrzymuje usługę epsonscansvc."""
    try:
        res = subprocess.run(["sc", "stop", "epsonscansvc"], capture_output=True, text=True, errors="ignore")
        return res.returncode == 0 or "STOPPED" in res.stdout.upper()
    except Exception:
        return False


def kill_epson_tasks(procs):
    """Wymusza zamknięcie wskazanych procesów."""
    killed = []
    failed = []
    for p in procs:
        try:
            r = subprocess.run(["taskkill", "/F", "/IM", p], capture_output=True, text=True, errors="ignore")
            if r.returncode == 0:
                killed.append(p)
            else:
                failed.append(p)
        except Exception:
            failed.append(p)
    return killed, failed


def is_windows_admin():
    """Sprawdza, czy bieżący proces posiada uprawnienia administratora w systemie Windows."""
    if not sys.platform.startswith("win"):
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def manage_epson_background_tasks(interactive=True):
    """Sprawdza i opcjonalnie zamyka procesy oraz usługi Epsona."""
    if not sys.platform.startswith("win"):
        return True

    procs = find_epson_tasks()
    svc_running = is_epson_service_running()

    if not procs and not svc_running:
        if interactive:
            print("\n[OK] " + t("bg_clean"))
        return True

    print("\n" + "=" * 62)
    print(" " + t("bg_detected_title"))
    print("=" * 62)
    if svc_running:
        print("  - " + t("bg_service_item"))
    if procs:
        print("  - " + t("bg_process_item", count=len(procs), list=', '.join(procs)))
    print("  " + t("bg_warning"))
    if not is_windows_admin():
        print("  [!] " + t("bg_admin_hint"))
    print("=" * 62)

    if interactive:
        ans = input("\n" + t("bg_prompt_kill")).strip().lower()
        if ans in ("", "t", "tak", "y", "yes"):
            if svc_running:
                print("  " + t("bg_stopping_svc"), end=" ")
                if stop_epson_service():
                    print(t("bg_svc_ok"))
                else:
                    print(t("bg_svc_fail"))
            if procs:
                killed, failed = kill_epson_tasks(procs)
                if killed:
                    print("  " + t("bg_killed", list=', '.join(killed)))
                if failed:
                    print("  " + t("bg_kill_failed", list=', '.join(failed)))
            print("[OK] " + t("bg_done") + "\n")
    return True


# ==============================================================================
# 1. BEZPOŚREDNIE USB NA WINDOWS (Win32 SetupAPI / ctypes)
# ==============================================================================
if sys.platform.startswith("win"):
    import ctypes
    from ctypes import wintypes as wt

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wt.DWORD),
            ("Data2", wt.WORD),
            ("Data3", wt.WORD),
            ("Data4", wt.BYTE * 8)
        ]

    GUID_USBPRINT = GUID(
        0x28D78FAD, 0x5A12, 0x11D1,
        (wt.BYTE * 8)(0xAE, 0x5B, 0x00, 0x00, 0xF8, 0x03, 0xA8, 0xC2)
    )

    class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wt.DWORD),
            ("InterfaceClassGuid", GUID),
            ("Flags", wt.DWORD),
            ("Reserved", ctypes.c_size_t)
        ]

    def find_usbprint_device_paths(vid_filter="04b8"):
        setupapi = ctypes.WinDLL("setupapi.dll")
        hDevInfo = setupapi.SetupDiGetClassDevsW(
            ctypes.byref(GUID_USBPRINT), None, None, 0x12
        )
        if hDevInfo == -1 or hDevInfo == 0:
            return []

        paths = []
        try:
            if_data = SP_DEVICE_INTERFACE_DATA()
            if_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            idx = 0
            while setupapi.SetupDiEnumDeviceInterfaces(hDevInfo, None, ctypes.byref(GUID_USBPRINT), idx, ctypes.byref(if_data)):
                idx += 1
                req_size = wt.DWORD(0)
                setupapi.SetupDiGetDeviceInterfaceDetailW(hDevInfo, ctypes.byref(if_data), None, 0, ctypes.byref(req_size), None)
                if req_size.value == 0:
                    continue

                detail_buf = ctypes.create_string_buffer(req_size.value)
                cb_size = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else (4 + ctypes.sizeof(wt.WCHAR))
                ctypes.memmove(detail_buf, ctypes.byref(wt.DWORD(cb_size)), 4)

                if setupapi.SetupDiGetDeviceInterfaceDetailW(hDevInfo, ctypes.byref(if_data), detail_buf, req_size, None, None):
                    device_path = ctypes.wstring_at(ctypes.byref(detail_buf, 4))
                    if not vid_filter or (f"vid_{vid_filter.lower()}" in device_path.lower()):
                        paths.append(device_path)
        finally:
            setupapi.SetupDiDestroyDeviceInfoList(hDevInfo)
        return paths


class WindowsDirectUsbTransport:
    _INIT = b"\x1b@"
    _ENTER_REMOTE = b"\x1b(R\x08\x00\x00REMOTE1"
    _EXIT_REMOTE = b"\x1b\x00\x00\x00"

    def __init__(self, vid_filter="04b8"):
        if not sys.platform.startswith("win"):
            raise RuntimeError("USB Direct mode is supported on Windows only.")

        paths = find_usbprint_device_paths(vid_filter)
        if not paths:
            paths = find_usbprint_device_paths(None)
            if not paths:
                raise IOError(
                    "USB printer device not found (no USBPRINT interface in system).\n"
                    "1. Check USB cable and verify the printer is powered ON.\n"
                    "2. Verify 'USB Printing Support' appears in Windows Device Manager."
                )

        self.device_path = paths[0]
        self.kernel32 = ctypes.WinDLL("kernel32.dll")
        self.kernel32.CreateFileW.argtypes = [wt.LPWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
        self.kernel32.CreateFileW.restype = wt.HANDLE
        self.kernel32.WriteFile.argtypes = [wt.HANDLE, ctypes.c_char_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
        self.kernel32.WriteFile.restype = wt.BOOL
        self.kernel32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_char_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
        self.kernel32.ReadFile.restype = wt.BOOL
        self.kernel32.CloseHandle.argtypes = [wt.HANDLE]
        self.kernel32.CloseHandle.restype = wt.BOOL

    def epctrl(self, command, payload):
        frame = command + struct.pack("<H", len(payload)) + bytes(payload)
        packet = self._INIT + self._ENTER_REMOTE + frame + self._EXIT_REMOTE

        handle = self.kernel32.CreateFileW(
            self.device_path, 0xC0000000, 0x00000003, None, 3, 0, None
        )
        INVALID_HANDLE_VALUE = wt.HANDLE(-1).value
        if handle == INVALID_HANDLE_VALUE or handle == 0:
            err = self.kernel32.GetLastError()
            raise IOError(f"Failed to open USB port (code: {err}). Please run console as Administrator.")

        try:
            written = wt.DWORD(0)
            in_buf = ctypes.create_string_buffer(packet, len(packet))
            if not self.kernel32.WriteFile(handle, in_buf, len(packet), ctypes.byref(written), None):
                err = self.kernel32.GetLastError()
                raise IOError(f"USB WriteFile failed (error: {err}).")

            time.sleep(0.25)
            read = wt.DWORD(0)
            rbuf = ctypes.create_string_buffer(4096)
            out = b""
            for _ in range(20):
                if self.kernel32.ReadFile(handle, rbuf, 4096, ctypes.byref(read), None):
                    if read.value > 0:
                        out += rbuf.raw[:read.value]
                        if b";" in out or b"\x0c" in out:
                            break
                time.sleep(0.08)

            if not out:
                raise IOError("Printer did not return a response over Direct USB.")
            return out
        finally:
            self.kernel32.CloseHandle(handle)


# ==============================================================================
# 2. KOMUNIKACJA WI-FI / LAN (SNMP UDP port 161)
# ==============================================================================
def _ber_tlv(tag, value):
    length = len(value)
    if length < 0x80:
        len_bytes = bytes([length])
    else:
        lb = []
        while length:
            lb.append(length & 0xFF)
            length >>= 8
        len_bytes = bytes([0x80 | len(lb)]) + bytes(reversed(lb))
    return bytes([tag]) + len_bytes + value


def _ber_oid(oid_str):
    parts = [int(x) for x in oid_str.split(".")]
    body = bytes([40 * parts[0] + parts[1]])
    for p in parts[2:]:
        if p < 0x80:
            body += bytes([p])
        else:
            stack = [p & 0x7F]
            p >>= 7
            while p:
                stack.append((p & 0x7F) | 0x80)
                p >>= 7
            body += bytes(reversed(stack))
    return _ber_tlv(0x06, body)


def build_snmp_get(oid_str, req_id=0x1234):
    varbind = _ber_tlv(0x30, _ber_oid(oid_str) + _ber_tlv(0x05, b""))
    pdu = _ber_tlv(0xA0, _ber_tlv(0x02, struct.pack(">I", req_id)) + _ber_tlv(0x02, b"\x00") + _ber_tlv(0x02, b"\x00") + _ber_tlv(0x30, varbind))
    return _ber_tlv(0x30, _ber_tlv(0x02, b"\x00") + _ber_tlv(0x04, b"public") + pdu)


def discover_epson_printers(timeout=1.5):
    """Skanuje lokalne podsieci w poszukiwaniu drukarek Epson (SNMP UDP port 161)."""
    subnets = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127.") and not ip.startswith("169.254."):
            subnets.add(".".join(ip.split(".")[:3]) + ".")
    except Exception:
        pass

    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254.") and ":" not in ip:
                subnets.add(".".join(ip.split(".")[:3]) + ".")
    except Exception:
        pass

    if not subnets:
        return []

    pkt = build_snmp_get(MODEL_NAME_OID)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if hasattr(socket, "SIO_UDP_CONNRESET"):
        try:
            sock.ioctl(socket.SIO_UDP_CONNRESET, False)
        except Exception:
            pass
    sock.settimeout(0.2)

    try:
        sock.sendto(pkt, ("255.255.255.255", 161))
    except Exception:
        pass

    for prefix in subnets:
        try:
            sock.sendto(pkt, (prefix + "255", 161))
        except Exception:
            pass
        for i in range(1, 255):
            try:
                sock.sendto(pkt, (f"{prefix}{i}", 161))
            except Exception:
                pass

    found = {}
    start = time.time()
    while time.time() - start < timeout:
        try:
            data, (from_ip, port) = sock.recvfrom(4096)
            text = data.decode("latin-1", "replace")
            m = re.search(r"EPSON\s+[\w\s-]+", text, re.IGNORECASE)
            if not m and "epson" not in text.lower():
                continue
            model = m.group(0).strip() if m else "Epson Printer"
            found[from_ip] = model
        except (socket.timeout, ConnectionResetError, OSError):
            continue
        except Exception:
            break
    sock.close()
    return [(ip, model) for ip, model in found.items()]


class SnmpTransport:
    def __init__(self, host, port=161, timeout=5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._rid = 0x4552

    def _query(self, oid_str):
        self._rid = (self._rid + 1) & 0x7FFFFFFF
        msg = build_snmp_get(oid_str, req_id=self._rid)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        try:
            sock.sendto(msg, (self.host, self.port))
            data, _ = sock.recvfrom(4096)
            return data
        finally:
            sock.close()

    def get_model_name(self):
        raw = self._query(MODEL_NAME_OID)
        text = raw.decode("latin-1", "replace")
        m = re.search(r"EPSON\s+[\w\s-]+", text, re.IGNORECASE)
        return m.group(0).strip() if m else "Epson Printer"

    def epctrl(self, command, payload):
        frame = command + struct.pack("<H", len(payload)) + bytes(payload)
        oid = OID_PREFIX + "." + ".".join(str(b) for b in frame)
        return self._query(oid)


# ==============================================================================
# 3. BUFOR WYDRUKU WINDOWS (Winspool API)
# ==============================================================================
class WinspoolTransport:
    _INIT = b"\x1b@"
    _ENTER_REMOTE = b"\x1b(R\x08\x00\x00REMOTE1"
    _EXIT_REMOTE = b"\x1b\x00\x00\x00"

    def __init__(self, printer_name):
        self.spool = ctypes.WinDLL("winspool.drv")
        self.printer_name = printer_name

    def epctrl(self, command, payload):
        class DOC_INFO_1(ctypes.Structure):
            _fields_ = [("pDocName", wt.LPWSTR), ("pOutputFile", wt.LPWSTR), ("pDatatype", wt.LPWSTR)]

        hPrinter = wt.HANDLE()
        if not self.spool.OpenPrinterW(self.printer_name, ctypes.byref(hPrinter), None):
            raise IOError(f"Could not open printer '{self.printer_name}' in Windows Spooler.")

        try:
            doc = DOC_INFO_1("epson_reset", None, "RAW")
            if not self.spool.StartDocPrinterW(hPrinter, 1, ctypes.byref(doc)):
                raise IOError("StartDocPrinter failed.")
            self.spool.StartPagePrinter(hPrinter)

            frame = command + struct.pack("<H", len(payload)) + bytes(payload)
            packet = self._INIT + self._ENTER_REMOTE + frame + self._EXIT_REMOTE

            written = wt.DWORD(0)
            in_buf = ctypes.create_string_buffer(packet, len(packet))
            self.spool.WritePrinter(hPrinter, in_buf, len(packet), ctypes.byref(written))
            self.spool.EndPagePrinter(hPrinter)
            self.spool.EndDocPrinter(hPrinter)

            time.sleep(0.3)
            out = b""
            read = wt.DWORD(0)
            rbuf = ctypes.create_string_buffer(4096)
            for _ in range(25):
                if not self.spool.ReadPrinter(hPrinter, rbuf, 4096, ctypes.byref(read)):
                    break
                if read.value == 0:
                    if out:
                        break
                    time.sleep(0.1)
                    continue
                out += rbuf.raw[:read.value]
                if b"\x0c" in out or b";" in out:
                    break
            return out
        finally:
            self.spool.ClosePrinter(hPrinter)


# ==============================================================================
# Operacje niskopoziomowe na pamięci EEPROM
# ==============================================================================
def read_eeprom_byte(transport, profile, addr):
    """Odczytuje 1 bajt z pamięci EEPROM."""
    read_key = profile["read_key"]
    payload = [read_key[0], read_key[1], 65, 190, 160, addr % 256, addr // 256]
    resp = transport.epctrl(b"||", payload)
    text = resp.decode("latin-1", "replace") if isinstance(resp, (bytes, bytearray)) else str(resp)

    match = re.search(r"EE:([0-9A-Fa-f]{6})", text)
    if not match:
        raise IOError(f"No EEPROM response for address {addr}. Received: {resp!r}")

    hex_data = match.group(1)
    addr_got, val_got = int(hex_data[:4], 16), int(hex_data[4:], 16)
    if addr_got != addr:
        raise IOError(f"Address mismatch: requested {addr}, received {addr_got}")
    return val_got


def write_eeprom_byte(transport, profile, addr, value):
    """Zapisuje 1 bajt do pamięci EEPROM z autoryzacją hasłem sprzętowym."""
    read_key = profile["read_key"]
    write_key = profile["write_key"]
    encoded_key = [0 if b == 0 else b + 1 for b in write_key]

    payload = ([read_key[0], read_key[1], 66, 189, 33, addr % 256, addr // 256, value] + encoded_key)
    resp = transport.epctrl(b"||", payload)
    text = resp.decode("latin-1", "replace") if isinstance(resp, (bytes, bytearray)) else str(resp)

    if ":OK;" not in text:
        raise IOError(f"Byte write failed (address {addr} = {value}). Response: {resp!r}")
    return True


# ==============================================================================
# Operacje wyższego poziomu (Odczyt, Backup, Reset, Przywracanie)
# ==============================================================================
def read_status(transport, profile, model_name):
    print("\n" + "=" * 62)
    print(" " + t("status_title", model=model_name))
    print("=" * 62)
    counters = profile.get("counters", [])
    if not counters:
        print("  " + t("status_no_counters"))
        print("  " + t("status_available_map", count=len(profile.get("reset", {}))))
    else:
        for counter_info in counters:
            name, byte_offsets = counter_info[0], counter_info[1]
            divider = counter_info[2] if len(counter_info) > 2 else None
            hex_bytes = [f"{read_eeprom_byte(transport, profile, b):02X}" for b in byte_offsets]
            raw_val = int("".join(reversed(hex_bytes)), 16)
            if divider:
                pct = (raw_val / divider)
                status_tag = " " + t("status_locked") if pct >= 100.0 else " " + t("status_normal") if pct < 80 else " " + t("status_warning")
                print(f"  {name:<36}: {pct:6.2f}% {status_tag} (raw: {raw_val})")
            else:
                print(f"  {name:<36}: {raw_val:8d} ({t('status_points')})")
    print("=" * 62 + "\n")


def make_backup(transport, profile, model_name, filepath=None):
    if not filepath:
        safe_name = re.sub(r"[^\w-]", "_", model_name.lower())
        filepath = f"eeprom_backup_{safe_name}.txt"

    print(t("backup_creating", path=filepath))
    lines = [
        f"# EEPROM Backup - Model: {model_name}",
        f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "# Address(dec) = Value(dec) [Hex]"
    ]
    reset_map = profile.get("reset", {})
    for addr in sorted(reset_map.keys()):
        val = read_eeprom_byte(transport, profile, addr)
        lines.append(f"{addr} = {val} [0x{val:02X}]")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("[OK] " + t("backup_success", count=len(reset_map), path=filepath))
    return filepath


def reset_counters(transport, profile, model_name, filepath=None):
    make_backup(transport, profile, model_name, filepath)
    print("\n" + t("reset_starting"))
    reset_map = profile["reset"]
    for addr, val in reset_map.items():
        print(f"  EEPROM [{addr:2d}] -> {val:3d} ... ", end="")
        write_eeprom_byte(transport, profile, addr, val)
        print("OK")

    print("\n" + "*" * 62)
    print(" " + t("reset_success_title"))
    print(" " + t("reset_steps_title"))
    print(" " + t("reset_step_1"))
    print(" " + t("reset_step_2"))
    print(" " + t("reset_step_3"))
    print("*" * 62 + "\n")


def restore_backup(transport, profile, filepath):
    print("\n" + t("restore_loading", path=filepath))
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise IOError(t("restore_not_found", path=filepath))

    entries = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\d+)\s*=\s*(\d+)", line)
        if m:
            addr, val = int(m.group(1)), int(m.group(2))
            entries[addr] = val

    if not entries:
        raise ValueError(t("restore_invalid", path=filepath))

    print(t("restore_found_entries", count=len(entries)))
    for addr, val in sorted(entries.items()):
        print(f"  EEPROM [{addr:2d}] -> {val:3d} ... ", end="")
        write_eeprom_byte(transport, profile, addr, val)
        print("OK")

    print("\n" + "*" * 62)
    print(" " + t("restore_success"))
    print(" " + t("reset_step_1"))
    print(" " + t("reset_step_2"))
    print("*" * 62 + "\n")


# ==============================================================================
# TRYB INTERAKTYWNEGO MENU (Wizard / TUI)
# ==============================================================================
def interactive_menu():
    global CURRENT_LANG

    # Wybór języka na starcie (jeśli nie wybrano w CLI)
    print("\n" + "=" * 62)
    print("                    OpenInkPad")
    print("   Author: Hypnos-IT (https://github.com/Hypnos-IT)")
    print("   Contact: admin@hypnos-it.eu  |  License: EUPL-1.2")
    print("=" * 62)

    lang_choice = input("\nLanguage / Jezyk [1: English (default), 2: Polski]: ").strip()
    if lang_choice in ("2", "pl", "polski"):
        set_language("pl")
    else:
        set_language("en")

    # 1. Sprawdzenie i zarządzanie zadaniami w tle
    manage_epson_background_tasks(interactive=True)

    # 2. Wybór metody połączenia
    transport = None
    transport_desc = ""
    detected_name = None

    while transport is None:
        print("\n" + t("conn_title"))
        print("  " + t("conn_opt_scan"))
        print("  " + t("conn_opt_wifi"))
        print("  " + t("conn_opt_usb"))
        print("  " + t("conn_opt_spooler"))
        print("  " + t("conn_opt_exit"))

        choice = input("\n" + t("conn_prompt")).strip()
        if choice in ("", "1"):
            print("\n" + t("conn_scan_start"))
            printers = discover_epson_printers(timeout=1.5)
            if not printers:
                print("\n[!] " + t("conn_scan_none"))
                print("    " + t("conn_scan_hint"))
                continue

            selected_ip = None
            selected_model = None
            if len(printers) == 1:
                p_ip, p_model = printers[0]
                print("\n[+] " + t("conn_scan_found", model=p_model, ip=p_ip))
                ans = input(t("conn_scan_confirm")).strip().lower()
                if ans in ("", "t", "tak", "y", "yes"):
                    selected_ip = p_ip
                    selected_model = p_model
            else:
                print("\n[+] " + t("conn_scan_multi", count=len(printers)))
                for idx, (p_ip, p_model) in enumerate(printers, 1):
                    print(f"  [{idx}] {p_ip:<16} - {p_model}")
                sel = input(t("conn_scan_select", count=len(printers))).strip()
                try:
                    s_idx = int(sel) - 1
                    if 0 <= s_idx < len(printers):
                        selected_ip, selected_model = printers[s_idx]
                except ValueError:
                    pass

            if selected_ip:
                print(t("conn_wifi_connecting", ip=selected_ip))
                try:
                    transport = SnmpTransport(selected_ip, timeout=5.0)
                    detected_name = selected_model or transport.get_model_name()
                    print("[OK] " + t("conn_wifi_response", name=detected_name))
                    transport_desc = f"Wi-Fi {selected_ip}"
                except Exception as e:
                    print("\n[!] " + t("conn_wifi_error", ip=selected_ip, err=e))
                    transport = None

        elif choice == "2":
            ip = input(t("conn_wifi_ip_prompt")).strip()
            if not ip:
                print("[!] " + t("conn_wifi_ip_empty"))
                continue
            print(t("conn_wifi_connecting", ip=ip))
            try:
                temp_transport = SnmpTransport(ip, timeout=2.5)
                detected_name = temp_transport.get_model_name()
                temp_transport.timeout = 5.0
                transport = temp_transport
                print("[OK] " + t("conn_wifi_response", name=detected_name))
                transport_desc = f"Wi-Fi {ip}"
            except Exception as e:
                print("\n[!] " + t("conn_wifi_error", ip=ip, err=e))
                print("    " + t("conn_wifi_hint"))
                transport = None

        elif choice == "3":
            print(t("conn_usb_connecting"))
            try:
                transport = WindowsDirectUsbTransport()
                print(t("conn_usb_found", path=transport.device_path))
                transport_desc = "USB Direct"
            except Exception as e:
                print(t("conn_usb_error", err=e))
                transport = None

        elif choice == "4":
            spool_name = input(t("conn_spooler_prompt")).strip()
            if not spool_name:
                spool_name = "EPSON L386 Series"
            transport = WinspoolTransport(spool_name)
            transport_desc = f"Spooler '{spool_name}'"

        elif choice == "0":
            print(t("conn_exit"))
            return

    # 3. Rozpoznanie i wybór profilu modelu
    model_name = None
    profile = None

    if detected_name:
        model_name, profile = resolve_model(detected_name)

    if profile:
        print("\n" + t("model_auto_detected", model=model_name))
        ch = input(t("model_use_detected")).strip().lower()
        if ch not in ("", "t", "tak", "y", "yes"):
            profile = None

    while profile is None:
        print("\n" + t("model_menu_title"))
        print("  " + t("model_opt_default"))
        print("  " + t("model_opt_custom"))
        print("  " + t("model_opt_search"))

        m_choice = input(t("model_prompt")).strip()
        if m_choice in ("", "1"):
            model_name, profile = resolve_model("L386")
        elif m_choice == "2":
            custom_m = input(t("model_enter_name")).strip()
            model_name, profile = resolve_model(custom_m)
            if not profile:
                print(t("model_not_found", name=custom_m))
        elif m_choice == "3":
            q = input(t("model_search_query")).strip()
            list_supported_models(q)

    print("\n" + t("model_active", model=model_name))

    # 4. Pętla menu akcji
    safe_name = re.sub(r"[^\w-]", "_", model_name.lower())
    default_backup = f"eeprom_backup_{safe_name}.txt"

    while True:
        print("\n" + "=" * 62)
        print(" " + t("menu_header", model=model_name, conn=transport_desc))
        print("=" * 62)
        print("  " + t("menu_opt_1"))
        print("  " + t("menu_opt_2"))
        print("  " + t("menu_opt_3"))
        print("  " + t("menu_opt_4"))
        print("  " + t("menu_opt_5"))
        print("  " + t("menu_opt_6"))
        print("  " + t("menu_opt_7"))
        print("  " + t("menu_opt_0"))
        print("=" * 62)

        action = input(t("menu_prompt")).strip()

        if action == "1":
            try:
                read_status(transport, profile, model_name)
            except Exception as e:
                print("\n" + t("op_error", err=e))
        elif action == "2":
            try:
                make_backup(transport, profile, model_name, default_backup)
            except Exception as e:
                print("\n" + t("op_error", err=e))
        elif action == "3":
            try:
                print("\n" + t("reset_warning", model=model_name))
                confirm = input(t("reset_confirm")).strip().lower()
                if confirm in ("tak", "t", "yes", "y"):
                    reset_counters(transport, profile, model_name, default_backup)
                    read_status(transport, profile, model_name)
                else:
                    print(t("reset_cancelled"))
            except Exception as e:
                print("\n" + t("op_error", err=e))
        elif action == "4":
            try:
                confirm = input(t("restore_confirm", path=default_backup)).strip().lower()
                if confirm in ("tak", "t", "yes", "y"):
                    restore_backup(transport, profile, default_backup)
                    read_status(transport, profile, model_name)
                else:
                    print(t("reset_cancelled"))
            except Exception as e:
                print("\n" + t("op_error", err=e))
        elif action == "5":
            manage_epson_background_tasks(interactive=True)
        elif action == "6":
            profile = None
            while profile is None:
                m_in = input(t("model_enter_name") + " (or 'list'): ").strip()
                if m_in.lower() in ("lista", "list"):
                    list_supported_models("")
                    continue
                model_name, profile = resolve_model(m_in)
                if not profile:
                    print(t("model_not_found", name=m_in))
            safe_name = re.sub(r"[^\w-]", "_", model_name.lower())
            default_backup = f"eeprom_backup_{safe_name}.txt"
            print(t("model_active", model=model_name))
        elif action == "7":
            new_lang = "pl" if CURRENT_LANG == "en" else "en"
            set_language(new_lang)
            print(t("lang_switched"))
        elif action == "0":
            print(t("conn_exit"))
            break
        else:
            print(t("invalid_choice"))


# ==============================================================================
# CLI (Wiersz poleceń z argumentami)
# ==============================================================================
def main():
    if len(sys.argv) == 1:
        interactive_menu()
        return

    parser = argparse.ArgumentParser(
        description="OpenInkPad - Service tool for 1270+ Epson printer models (Hypnos-IT | License: EUPL-1.2)."
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--scan", action="store_true", help="Auto-scan local network for Epson printers")
    group.add_argument("--host", help="Printer Wi-Fi/LAN IP address (e.g. 192.168.1.67)")
    group.add_argument("--usb", action="store_true", help="Direct USB connection on Windows (Win32 API)")
    group.add_argument("--spooler", help="Windows Print Spooler name (e.g. 'EPSON L386 Series')")

    parser.add_argument("--interactive", action="store_true", help="Run interactive menu")
    parser.add_argument("--model", help="Printer model (e.g. 'L386', 'L3150', 'ET-2700'). Default: auto-detect or L386.")
    parser.add_argument("--list-models", nargs="?", const="", help="List supported models (optional search filter)")
    parser.add_argument("--backup-file", help="Custom path for EEPROM backup file")
    parser.add_argument("--lang", choices=["en", "pl"], default="en", help="Language for output (en/pl). Default: en")

    parser.add_argument("action", nargs="?", choices=["odczyt", "read", "backup", "dump", "reset", "przywroc", "restore"],
                        help="Action: 'read'/'odczyt', 'backup'/'dump', 'reset', 'restore'/'przywroc'")

    args = parser.parse_args()

    set_language(args.lang)

    if args.interactive:
        interactive_menu()
        return

    if args.list_models is not None:
        list_supported_models(args.list_models)
        return

    if args.scan:
        print(t("conn_scan_start"))
        printers = discover_epson_printers(timeout=1.5)
        if not printers:
            print("[!] " + t("conn_scan_none"), file=sys.stderr)
            sys.exit(1)
        if not args.action:
            print(f"\nFound {len(printers)} Epson printer(s):")
            for p_ip, p_model in printers:
                print(f"  {p_ip:<16} - {p_model}")
            print(f"\nUsage: python openinkpad.py --host {printers[0][0]} read")
            return
        args.host = printers[0][0]
        detected_name = printers[0][1]
        print(f"[+] Using found printer: {detected_name} ({args.host})")

    if not args.action:
        interactive_menu()
        return

    if not (args.host or args.usb or args.spooler):
        print(t("cli_err_conn"), file=sys.stderr)
        sys.exit(1)

    # Sprawdzenie procesów w tle (w trybie CLI tylko informacja)
    manage_epson_background_tasks(interactive=False)

    detected_name = None
    if args.usb:
        transport = WindowsDirectUsbTransport()
        print(t("conn_usb_found", path=transport.device_path))
    elif args.host:
        try:
            transport = SnmpTransport(args.host, timeout=3.0)
            detected_name = transport.get_model_name()
            transport.timeout = 5.0
            print(t("conn_wifi_response", name=detected_name))
        except Exception as e:
            print(t("conn_wifi_error", ip=args.host, err=e), file=sys.stderr)
            sys.exit(1)
    elif args.spooler:
        transport = WinspoolTransport(args.spooler)

    model_name = None
    profile = None

    if args.model:
        model_name, profile = resolve_model(args.model)
        if not profile:
            print(t("cli_model_not_found", name=args.model), file=sys.stderr)
            print(t("cli_model_list_hint"), file=sys.stderr)
            sys.exit(1)
    elif detected_name:
        model_name, profile = resolve_model(detected_name)

    if not profile:
        model_name, profile = resolve_model("L386")
        print(t("cli_default_profile"))
    else:
        print(t("model_active", model=model_name))

    backup_file = args.backup_file
    cmd = args.action.lower()

    try:
        if cmd in ("odczyt", "read"):
            read_status(transport, profile, model_name)
        elif cmd in ("backup", "dump"):
            make_backup(transport, profile, model_name, backup_file)
        elif cmd == "reset":
            print("\n" + t("reset_warning", model=model_name))
            confirm = input(t("reset_confirm"))
            if confirm.strip().lower() in ["tak", "yes", "t", "y"]:
                reset_counters(transport, profile, model_name, backup_file)
                read_status(transport, profile, model_name)
            else:
                print(t("reset_cancelled"))
        elif cmd in ("przywroc", "restore"):
            safe_default_name = re.sub(r"[^\w-]", "_", model_name.lower())
            file_to_restore = backup_file or f"eeprom_backup_{safe_default_name}.txt"
            confirm = input(t("restore_confirm", path=file_to_restore))
            if confirm.strip().lower() in ["tak", "yes", "t", "y"]:
                restore_backup(transport, profile, file_to_restore)
                read_status(transport, profile, model_name)
            else:
                print(t("reset_cancelled"))
    except Exception as err:
        print(f"\n[ERROR]: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
