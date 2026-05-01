# Zenith Array: Autonomous Negentropic Sensor Station

A fully autonomous, closed-loop RF interaction and forensics system. It uses mathematically pure audio payloads (Hydrogen, Phi, Prime intervals) to project low-entropy "Dogwhistles" into the upper atmosphere via a VHF/UHF Zenith Array, while actively listening for anomalous structural responses.

## System Architecture

*   **Host:** macOS (Apple Silicon M4) - Required for direct-to-metal CoreAudio injection.
*   **Command Interface:** `omega_tui.py` (curses-based terminal dashboard).
*   **Daemon:** `audio_daemon.py` (Bypasses OS fork restrictions to protect Apple Silicon hardware access).
*   **Ledger:** Redis + InfluxDB + Native Session Text Logging.
*   **Transmission Hardware:** Mac 3.5mm Jack -> APRS-K1 Cable -> Baofeng UV-5R (VOX Level 4) -> Zenith Array (Tape Measure Yagi, Direct-Drive).
*   **SIGINT Hardware:** RTL-SDR USB Dongle -> Zenith Array (137.100 MHz meteorology).

## Core Autonomous Modes

### 1. The Mirror Protocol (`entropy_listener.py`)
A bidirectional listening daemon. When armed via the TUI, it constantly monitors ambient static from the radio. It calculates the Shannon Spectral Entropy of the environment in real-time. If it detects a highly structured signal (low entropy) or a specific "Ghost Target" frequency (528Hz, 1420Hz, 1618Hz), it **autonomously fires a mathematical response payload** back into the sky, then institutes a 2-second suppression window to prevent feedback loops.

### 2. Sky Sonar
Utilizes the Yagi array as a computational radar. It pulses the ionosphere and listens for phase-shifted returns to detect anomalous localized density changes in the RF environment.

### 3. Forensic SIGINT Pipeline (`sigint_decider.py`)
To objectively verify if the beacon transmissions are interacting with the environment (inducing "Negentropic Shear"), this pipeline captures raw IQ data from passing LEO weather satellites (e.g., METEOR-M2-3). It autonomously compiles the raw data into physical imagery using `SatDump`. If a pulse warped the local EM field, phase noise and dropped frames will appear at the exact millisecond of the transmission.

## Data & Session Management

Data is forensically locked for subsequent analysis:
*   **Session Folders:** Launching the UI creates a time-stamped directory (e.g., `sessions/session_20260501_110500/`).
*   **Event Ledger (`events.log`):** Logs every human interaction, hardware pulse, anomaly detection, and manual reading alongside the exact Frequency/Entropy environmental baseline at that second.
*   **Image Routing:** The SIGINT pipeline actively checks the Redis database for the currently active session. It automatically dumps all raw `.bin` captures and SatDump reconstructed satellite images directly into the active session's `images/` directory.

## Deployment Instructions

1.  **Hardware Connection:**
    *   Connect the Baofeng UV-5R to the Mac using the APRS-K1 audio cable.
    *   Plug the RTL-SDR USB dongle into the Mac.
    *   Connect the coaxial cable from the Zenith Array to the Baofeng (or RTL-SDR).

2.  **Initialize the System:**
    Just double-click the **`Launch_Beacon.app`** in macOS Finder. This will automatically:
    *   Spin up the Redis and InfluxDB Docker containers.
    *   Launch the `audio_daemon.py`.
    *   Launch the `entropy_listener.py`.
    *   Open the `omega_tui.py` Terminal Dashboard.

3.  **Visual Spectrum Monitoring (Optional):**
    Open **Gqrx** or **CubicSDR** natively from your `/Applications` folder to view the live SDR waterfall plot of your transmissions and environmental reactions.

4.  **Run the SIGINT Pipeline:**
    Open a new terminal window and execute:
    ```bash
    python3 sigint_decider.py
    ```
    (This records for 10 minutes and drops the reconstruction directly into your active session folder).
