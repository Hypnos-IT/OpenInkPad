# OpenInkPad

[![Pobierz najnowszą wersję](https://img.shields.io/badge/Pobierz_najnowszą_wersję-Pobierz_ZIP-2ea44f?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Hypnos-IT/OpenInkPad/releases/latest)

[![Licencja: EUPL 1.2](https://img.shields.io/badge/Licencja-EUPL%201.2-blue.svg)](LICENSE)
[![Python: 3.x](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Wersja](https://img.shields.io/github/v/release/Hypnos-IT/OpenInkPad?color=blue&label=Najnowsza%20wersja)](https://github.com/Hypnos-IT/OpenInkPad/releases/latest)

[English version](README.md)

OpenInkPad to samodzielne narzędzie w Pythonie 3 do odczytu, tworzenia kopii zapasowej, zerowania i przywracania licznika zużycia pampersa (Waste Ink Pad Counter) dla ponad 1270 modeli drukarek Epson (w tym serii L386, L3150, EcoTank ET, XP, WF, Stylus oraz Artisan).

Napisane w standardowym Pythonie bez zewnętrznych bibliotek.

Program ma prosty kreator w terminalu, automatyczny skaner sieci lokalnej wykrywający drukarki Wi-Fi bez wpisywania adresu IP, moduł zamykania procesów tła blokujących port oraz bezpośrednią obsługę połączenia USB w systemie Windows przez Win32 API.

---

### Dlaczego powstał ten projekt?

Zaczęło się od drukarki mojej mamy, która nagle przestała drukować przez programową blokadę przepełnienia pampersa.

Drukarki nie powinny stawać się bezużyteczne z powodu zwykłego licznika w pamięci, zwłaszcza gdy komercyjne programy żądają kilkudziesięciu złotych za każdy jednorazowy klucz resetujący. Przygotowałem to narzędzie jako otwarty, darmowy program, żeby każdy mógł zresetować swój licznik samodzielnie.

---

## Wesprzyj projekt
 
Jeśli ten program uratował Twoją drukarkę, zaoszczędził Ci zakupu klucza resetującego lub pomaga Ci w naprawie sprzętu klientów w pracy, możesz postawić mi kawę:

[![GitHub Sponsors](https://img.shields.io/badge/GitHub_Sponsors-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Hypnos-IT)
[![Ko-fi](https://img.shields.io/badge/Postaw_kawę_na_Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/hypnosit)

---

## Tryb interaktywnego menu (zalecany)

Uruchom program w PowerShell lub CMD jako Administrator:

```powershell
python .\openinkpad.py
```

Uprawnienia administratora są potrzebne, aby program mógł wyłączyć usługi w tle i komunikować się bezpośrednio przez kabel USB.

Kreator prowadzi krok po kroku:
1. Wybór języka (polski lub angielski).
2. Zamknięcie programów monitorujących Epsona (`epsonscansvc`, `Epson Status Monitor`), które mogą blokować dostęp do portu.
3. Wybór połączenia: automatyczny skan sieci, ręczny adres IP, bezpośrednie USB lub bufor wydruku Windows.
4. Wybór modelu z bazy ponad 1270 urządzeń lub automatyczne rozpoznanie przez sieć.
5. Odczyt stanu, zapis kopii EEPROM do pliku, zerowanie licznika lub przywrócenie danych z kopii.

---

## Wymagania wstępne i zadania w tle

Programy monitorujące Epsona stale odpytują urządzenie, co może blokować port i odrzucać polecenia serwisowe.

Kreator potrafi zamknąć je automatycznie. Jeśli wolisz zrobić to ręcznie:

### 1. Zatrzymanie usługi skanowania (epsonscansvc)
W PowerShell jako administrator:
```powershell
Stop-Service -Name "epsonscansvc" -Force -ErrorAction SilentlyContinue
```
Albo w CMD:
```cmd
net stop epsonscansvc
```

### 2. Zamknięcie procesów w tle
W PowerShell:
```powershell
Get-Process *epson*, *seiko* -ErrorAction SilentlyContinue | Stop-Process -Force
```
Możesz też zamknąć procesy takie jak `Epson Status Monitor` czy `E_IATIA01.EXE` w Menedżerze zadań (Ctrl + Shift + Esc).

---

## Obsługa przez wiersz poleceń (tryb CLI)

Do skryptów i automatyzacji można przekazywać parametry bezpośrednio.

### Połączenie sieciowe / Wi-Fi (zalecane)

```powershell
# Automatyczne znalezienie drukarki w sieci i odczyt
python .\openinkpad.py --scan read

# Odczyt ze wskazanego adresu IP
python .\openinkpad.py --host 192.168.1.67 read

# Kopia zapasowa EEPROM do pliku
python .\openinkpad.py --host 192.168.1.67 backup

# Zerowanie liczników do 0%
python .\openinkpad.py --host 192.168.1.67 reset

# Przywrócenie rejestrów z pliku kopii
python .\openinkpad.py --host 192.168.1.67 restore
```

### Bezpośredni kabel USB (Windows)

Uruchom PowerShell lub CMD jako Administrator:

```powershell
python .\openinkpad.py --usb read
python .\openinkpad.py --usb reset
```

---

## Flagi i opcje wiersza poleceń

| Flaga | Wartość | Opis |
|---|---|---|
| `--scan` | brak | Skanowanie lokalnej sieci w poszukiwaniu drukarki Epson (SNMP UDP port 161). |
| `--host` | `<IP>` | Adres IP drukarki w sieci lokalnej (Wi-Fi lub kabel). |
| `--usb` | brak | Bezpośrednie połączenie USB przez Win32 API (wymaga uprawnień administratora). |
| `--model` | `<NAZWA>` | Nazwa modelu drukarki (np. `L386`, `L3150`, `ET-2700`). |
| `--list-models` | `[filtr]` | Wyszukanie lub lista obsługiwanych modeli z pliku `prn_models.py`. |
| `--backup-file` | `<ścieżka>` | Własna ścieżka do pliku kopii zapasowej EEPROM. |
| `--spooler` | `"<Nazwa>"` | Połączenie przez bufor wydruku Windows Spooler. |
| `--lang` | `en` / `pl` | Język komunikatów (`en` domyślny, `pl` dla polskiego). |

---

## Baza obsługiwanych modeli

Plik `prn_models.py` zawiera profile dla ponad 1270 modeli:

```powershell
# Pełna lista modeli
python .\openinkpad.py --list-models

# Filtrowanie po serii
python .\openinkpad.py --list-models L3
python .\openinkpad.py --list-models ET-
python .\openinkpad.py --list-models XP
```

---

## Procedura resetu i ponowne uruchomienie urządzenia

1. Sprawdź stan licznika komendą `read`. Gdy licznik osiągnie 100%, drukarka blokuje pracę.
2. Uruchom `reset` i potwierdź wpisując `tak`. Skrypt utworzy kopię zapasową przed zapisem.
3. Wyłącz drukarkę przyciskiem zasilania na obudowie.
4. Odczekaj 10 sekund i włącz ją ponownie. Urządzenie załaduje wyzerowane rejestry z pamięci EEPROM i wznowi normalną pracę.

---

## Konserwacja fizyczna (poduszki na zużyty tusz)

Program zeruje wyłącznie licznik w pamięci urządzenia, nie usuwa tuszu z filców chłonnych.

Przed dalszym drukowaniem:
* Wyjmij pojemnik z tyłu obudowy, wypłucz wkłady filcowe pod bieżącą wodą i wysusz je do sucha (albo wymień na nowe), lub
* Wyprowadź wężyk odpływowy do zewnętrznej butelki na zużyty tusz.

---

## Podziękowania i źródła

Projekt korzysta z ustaleń i otwartych danych udostępnionych przez społeczność:

* **[epson_print_conf](https://github.com/Ircama/epson_print_conf)** (autor: **Ircama**): badania nad protokołem Epson ESC/I, tunelowaniem zapytań przez SNMP UDP i rejestrami EEPROM.
* **[ReInkPy](https://codeberg.org/atufi/reinkpy/)** (autor: **atufi**): baza profili, mapowanie adresów pamięci EEPROM i definicje wag liczników.
* **[epson-waste-reset](https://github.com/MAkcanca/epson-waste-reset)** (autor: **MAkcanca**): zebranie i przygotowanie bazy ponad 1270 modeli w pliku `prn_models.py`.

---

## Zrzeczenie się odpowiedzialności i bezpieczeństwo

Program modyfikuje pamięć EEPROM drukarki. Używasz go na własną odpowiedzialność.

Pamiętaj o dwóch kwestiach:
* Wyciek tuszu: sam reset licznika nie usuwa płynu z poduszek. Drukowanie z pełnymi wkładami doprowadzi do przelania atramentu do wnętrza obudowy i zalania elektroniki.
* Przerwanie zapisu: nie odłączaj kabli ani nie wyłączaj zasilania podczas procedury zapisu do pamięci. Przed każdą zmianą skrypt tworzy kopię bezpieczeństwa, z której można przywrócić dane.

Autor nie odpowiada za ewentualne uszkodzenia sprzętu, wycieki tuszu ani utratę danych.

---

## Licencja i autor

**Autor:** [Hypnos-IT](https://github.com/Hypnos-IT)  
**Kontakt:** admin@hypnos-it.eu  
**Licencja:** [EUPL-1.2](LICENSE)

Oprogramowanie udostępniane jest na warunkach licencji **European Union Public Licence v1.2 (EUPL-1.2)**.

* Użytkownicy oraz punkty napraw mogą bezpłatnie korzystać z programu do celów prywatnych i zarobkowych.
* Licencja EUPL zawiera klauzulę copyleft. Wszystkie projekty pochodne lub modyfikacje muszą pozostać otwarte na warunkach EUPL lub licencji kompatybilnej.
* Zgodnie z art. 15 licencji EUPL prawem właściwym jest prawo państwa członkowskiego Unii Europejskiej, w którym siedzibę lub miejsce zamieszkania ma licencjodawca.

Pełny tekst licencji znajduje się w pliku [LICENSE](LICENSE).
