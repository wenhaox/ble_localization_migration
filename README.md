# BLE AoA Tag Port for u-blox XPLR-AOA-3

This repository documents and implements a port of the u-blox C209 AoA tag behavior onto a Nordic nRF platform. The main goal is to make a Nordic-based tag look compatible enough with the u-blox ANT-B10 / ANT-B11 anchor stack that the anchor will detect it, synchronize to it, and report direction estimates.

The key technical result in this repo is that a Nordic `direction_finding_connectionless_tx`-style beacon can be made visible to the u-blox anchor by matching the parts of the C209 advertising behavior that the anchor expects, especially:

- Bluetooth LE extended advertising
- periodic advertising with AoA CTE
- Eddystone-UID service data
- the `NINA-B4TAG` namespace used by the default u-locateEmbed filter
- a unique 6-byte instance ID derived from the device BLE address

This repo also includes a small host-side dashboard that visualizes live `+UUDF` angle reports from the anchor.

## Introduction

### Problem statement

u-blox ships the C209 tag as part of the XPLR-AOA-3 ecosystem, but the stock Nordic direction-finding sample is not directly recognized by the u-blox anchor firmware. The anchor expects a specific advertising format and namespace in addition to a valid CTE train.

This project studies the original C209 firmware, identifies the minimum behavior required for compatibility, and ports that behavior onto a Nordic sample app that can be built for newer Nordic boards, including nRF54-family targets.

### Target application

The target use case is a BLE angle-of-arrival demo or prototype where:

- a Nordic development board acts as the transmitting tag
- a u-blox ANT-B10 or ANT-B11 acts as the receiving anchor
- the anchor reports `+UUDF` angle messages
- a local host dashboard plots the reported AoA / elevation values

### High-level architecture

1. `nrf54_aoa_tag/` transmits BLE extended advertising and periodic advertising with an AoA CTE.
2. The advertising payload includes Eddystone-UID data with the `NINA-B4TAG` namespace.
3. A u-blox anchor receives the tag, computes direction, and emits `+UUDF` reports over serial.
4. `host/dashboard.py` reads those serial reports and visualizes active tags.

### Key features

- Ports the beacon side of the original C209 behavior to a Nordic sample-based app.
- Preserves the `NINA-B4TAG` Eddystone namespace required by default u-blox filtering.
- Fills the Eddystone instance ID from the BLE MAC address so each tag appears unique.
- Sets transmit power through Nordic vendor-specific HCI commands.
- Includes a simple live dashboard for multi-tag visualization from `+UUDF` serial output.
- Vendors the original C209 firmware and hardware docs for side-by-side comparison.

### Performance summary

This repo is currently focused on functional compatibility rather than full benchmarking.

- RF band: 2.4 GHz BLE
- CTE length: 160 us
- CTE count per periodic advertising event: 1
- TX power target in the port: `+4 dBm`
- Periodic advertising interval in the current port: `32` BLE units (`40 ms`)

Not yet fully characterized in this repo:

- localization accuracy
- discovery latency
- maximum range
- energy consumption on the new Nordic platform
- battery-powered runtime

For indicative power numbers on the original C209 hardware, see the upstream u-blox README in [c209-aoa-tag/README.md](c209-aoa-tag/README.md).

## Repository Layout

- [nrf54_aoa_tag](nrf54_aoa_tag)  
  The Nordic-based AoA tag port. This is the main firmware deliverable.
- [c209-aoa-tag](c209-aoa-tag)  
  Vendored upstream/reference firmware and hardware files from u-blox C209.
- [host/dashboard.py](host/dashboard.py)  
  Local host visualizer for `+UUDF` reports.

## Hardware

### Anchor / receiver side

- u-blox ANT-B10 or ANT-B11 Bluetooth Direction Finding anchor
- commonly used with the XPLR-AOA-3 kit

### Tag / transmitter side

Two tag implementations are represented in this repo:

- Original/reference tag: u-blox C209, based on the NINA-B4 / nRF52833 platform
- Port target used for this project: Nordic [nRF54L15 DK](https://www.nordicsemi.com/Products/Development-hardware/nRF54L15-DK), using the `nrf54l15dk/nrf54l15/cpuapp` board target
- Additional board configs are present under `nrf54_aoa_tag/` for:
  - `nrf54l15dk/nrf54l10/cpuapp`
  - `nrf54l15dk/nrf54l05/cpuapp`
  - `nrf54lm20dk/nrf54lm20a/cpuapp`
  - `nrf54lv10dk/nrf54lv10a/cpuapp`
  - `nrf5340dk/nrf5340/cpuapp`
  - `nrf52833dk/nrf52833`
  - `nrf52833dk/nrf52820`

The Nordic nRF54L15 DK product page describes it as the development kit for the nRF54L15, nRF54L10, and nRF54L05 wireless SoCs, with the nRF54L15 mounted on the board and the other two emulated. Key listed features include a 2.4 GHz antenna, SEGGER J-Link OB, onboard LEDs/buttons, and virtual serial ports.

### Additional peripherals

Required for the basic demo:

- no external sensors or custom add-on peripherals are required for the ported tag firmware
- one USB connection for the Nordic development board
- one USB-C connection for the anchor
- one serial connection from the anchor to the host running the dashboard

Optional / reference-only:

- the original C209 hardware design files are included in [c209-aoa-tag/HW_Design](c209-aoa-tag/HW_Design)
- the original u-blox helper scripts for DFU and BLE AT control are in [c209-aoa-tag/scripts](c209-aoa-tag/scripts)

### Hardware modifications

- No board-level rework, jumpers, custom PCB changes, or enclosure modifications are required for the demo setup documented in this repo.
- The demo setup is simply the Nordic development board powered over USB and the anchor powered over USB-C.
- If you are reproducing the original C209 hardware, refer to:
  - [C209 schematic PDF](c209-aoa-tag/HW_Design/C209_Schematic_NINA-B4.pdf)
  - [C209 BOM PDF](c209-aoa-tag/HW_Design/C209-V2_R2-BOM-5.pdf)
  - [C209 board file](c209-aoa-tag/HW_Design/C209.brd)

### Power subsystem

This demo is powered directly from USB and USB-C sources. There is no battery-powered configuration, no custom regulator design, and no runtime estimate documented for this setup.

Known reference information:

- the original C209 firmware upstream documents power tradeoffs vs periodic advertising interval
- the current port uses a much faster periodic interval (`40 ms`) than a low-power deployment would likely use

### RF specifications

- Radio: Bluetooth LE with direction finding support
- Frequency band: 2.4 GHz
- Direction finding mode: AoA CTE transmission
- CTE length: `160 us`
- CTE count per periodic advertising event: `1`
- Extended advertising data includes:
  - Flags
  - Eddystone UUID `0xFEAA`
  - Eddystone-UID service data
  - namespace `NINA-B4TAG`
  - 6-byte instance ID
- TX power: `+4 dBm` requested via Nordic vendor-specific HCI command

Compliance note:

- This repo is for development and evaluation. Any productization effort should re-check RF, antenna, region, and certification requirements on the actual shipping hardware.

## Software Environment

### Firmware

#### Reference firmware

The vendored u-blox C209 firmware README states:

- nRF Connect SDK `v2.1.0`
- West build flow
- board `ubx_evkninab4_nrf52833`

See [c209-aoa-tag/README.md](c209-aoa-tag/README.md).

#### Ported firmware

The ported app under `nrf54_aoa_tag/` is based on Nordic’s `direction_finding_connectionless_tx` sample and is validated here with nRF Connect SDK Toolchain `v3.2.1`.

Build system:

- CMake
- West
- Zephyr / nRF Connect SDK

Validated target/toolchain combination for this project:

- board: `nrf54l15dk/nrf54l15/cpuapp`
- toolchain / SDK environment: nRF Connect SDK Toolchain `v3.2.1`

Important files:

- [nrf54_aoa_tag/src/main.c](nrf54_aoa_tag/src/main.c)
- [nrf54_aoa_tag/prj.conf](nrf54_aoa_tag/prj.conf)
- [nrf54_aoa_tag/CMakeLists.txt](nrf54_aoa_tag/CMakeLists.txt)

### Host software

The host visualizer is currently:

- [host/dashboard.py](host/dashboard.py)

Python dependencies are not yet locked at the repo root, but the current dashboard requires:

- Python 3
- `customtkinter`
- `pyserial`

The vendored C209 helper scripts additionally use:

- `bleak==0.19.4`
- `numpy==1.23.3`

See [c209-aoa-tag/scripts/requirements.txt](c209-aoa-tag/scripts/requirements.txt).

### Programming / debugging tools

- `west`
- nRF Connect for VS Code or another working NCS environment
- SEGGER / onboard debugger compatible with the selected Nordic board
- `nrfutil` if using the original C209 DFU workflow
- serial terminal for firmware logs and anchor `+UUDF` output

### Radio configuration used by the port

From the current `nrf54_aoa_tag` implementation:

- Extended advertising enabled
- Periodic advertising enabled
- Broadcaster role enabled
- Direction finding enabled
- Connectionless AoA CTE TX enabled
- AoD TX disabled
- Eddystone-UID namespace required by anchor default filtering

## Reproducibility Guide

### 1. Hardware setup

Minimum demo setup:

1. One Nordic nRF54L15 DK flashed with the ported tag firmware
2. One u-blox ANT-B10 or ANT-B11 anchor configured to report `+UUDF`
3. One host computer connected to the anchor serial output

For the setup used in this project:

- the nRF54L15 DK is powered directly over USB
- the anchor is powered directly over USB-C
- no extra wiring, jumper changes, or external peripherals are required

If you need reference hardware details for the original tag, use the files under [c209-aoa-tag/HW_Design](c209-aoa-tag/HW_Design).

### 2. Environment setup

Install a Nordic build environment:

1. Install nRF Connect for Desktop and the Toolchain Manager, or otherwise install a working NCS + West environment.
2. Open a shell where `west` and the Zephyr environment are available.

Install host Python packages for the dashboard:

```bash
python3 -m pip install -r host/requirements.txt
```

Optional helper scripts:

```bash
python3 -m pip install -r c209-aoa-tag/scripts/requirements.txt
```

### 3. Build the ported firmware

The recommended workflow for this project is to use the nRF Connect extension in VS Code rather than building manually from the command line.

Suggested GUI workflow:

1. Open VS Code with the nRF Connect extension installed.
2. Add `nrf54_aoa_tag/` as an existing application.
3. Select nRF Connect SDK Toolchain `v3.2.1`.
4. Create a build configuration for board `nrf54l15dk/nrf54l15/cpuapp`.
5. Use the extension's **Build** button / GUI action to build the firmware.

Other valid board targets are listed in [nrf54_aoa_tag/sample.yaml](nrf54_aoa_tag/sample.yaml).

Optional command-line equivalent:

```bash
west build -p always -s nrf54_aoa_tag -b nrf54l15dk/nrf54l15/cpuapp
```

### 4. Flash the firmware

Use the nRF Connect VS Code extension GUI to flash the board after a successful build.

Suggested GUI workflow:

1. Connect the nRF54L15 DK over USB.
2. In the nRF Connect VS Code extension, select the correct build configuration.
3. Use the extension's **Flash** button / GUI action to program the board.

Optional command-line equivalent:

```bash
west flash
```

If you are working with the original C209 DFU flow instead, refer to the steps in [c209-aoa-tag/README.md](c209-aoa-tag/README.md).

### 5. Run the demo

1. Power or flash the tag board.
2. Open a serial console to the tag if you want to inspect firmware logs.
3. Confirm expected startup messages similar to:
   - `Starting Connectionless Beacon Demo`
   - `Bluetooth initialization...success`
   - `Set advertising data...success`
   - `Enable CTE...success`
   - `AoA tag running. Anchor should detect namespace NINA-B4TAG.`
4. Start the u-blox anchor side.
5. Confirm the anchor emits `+UUDF:` messages.
6. Update `SERIAL_PORT` in [host/dashboard.py](host/dashboard.py) if needed.
7. Run:

```bash
python3 host/dashboard.py
```

### 6. Expected behavior

When the port is working:

- the u-blox anchor detects the tag without changing its default `NINA-B4TAG` namespace filter
- `+UUDF` lines appear on the anchor serial interface
- the dashboard shows active tags and plots AoA / elevation positions

### 7. Testing and measurement

This repo currently supports functional verification more than formal benchmarking.

Recommended checks:

1. Tag appears on the anchor only after Eddystone-UID compatibility changes are present.
2. Changing boards still preserves:
   - Eddystone namespace
   - MAC-derived instance ID
   - periodic advertising
   - AoA CTE transmission
3. Dashboard updates correctly when multiple tags are active.

This repository does not include a formal dataset or benchmark suite. The testing in scope for this port is interoperability testing:

- can the Nordic-based tag be detected by the u-blox anchor
- do `+UUDF` direction messages appear
- does the dashboard visualize those live updates correctly

Metrics that are not yet measured in this repo:

- angle stability over time
- reacquisition time after reset
- current draw on the nRF54-based platform
- maximum reliable anchor-tag spacing

### 8. Troubleshooting

#### Anchor does not detect the tag

Check:

- Eddystone UUID `0xFEAA` is present
- namespace is exactly `NINA-B4TAG`
- extended advertising started successfully
- periodic advertising started successfully
- CTE TX enabled successfully

#### Tag builds but not on your chosen board

Check:

- board target name matches one of the supplied board configs
- your NCS version matches the API level expected by this port
- your board actually supports the Bluetooth direction-finding feature set you need

#### Dashboard shows stale tags

The current dashboard prunes tags after `10` seconds without updates. If your anchor reports more slowly than that, increase `STALE_SECONDS` in [host/dashboard.py](host/dashboard.py).

#### Dashboard does not show any tags

Check:

- the host is listening to the correct serial device
- the anchor is outputting `+UUDF:` lines
- Python packages `customtkinter` and `pyserial` are installed

### 9. Offline mode

Once toolchains are installed locally, the project can be built and run offline.

Helpful offline assets already in the repo:

- original C209 reference firmware
- original C209 hardware PDFs and board files
- local dashboard
- helper scripts

## Important Compatibility Notes

The most important compatibility finding from this project is:

> A plain Nordic direction-finding beacon is not enough for u-blox anchor compatibility; the advertising payload must also match the expected Eddystone-UID structure and namespace.

The key implementation lives in:

- [nrf54_aoa_tag/src/main.c](nrf54_aoa_tag/src/main.c)
- [c209-aoa-tag/src/bt_adv.c](c209-aoa-tag/src/bt_adv.c)
