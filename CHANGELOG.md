# Changelog: Negentropy Beacon Service

All notable changes to this project will be documented in this file.

## [Unreleased] - Current Active Build

### Added
*   **Autonomous Sensor Station (`entropy_listener.py`)**: Implemented a real-time listening script using `sounddevice` and `scipy`. Calculates normalized Shannon Spectral Entropy of incoming audio via FFT and automatically triggers `.wav` recording when negentropic (highly structured) signals are detected, ignoring chaotic static.
*   **Negentropic Shear Audio Engine**: Upgraded `prime_pulse_wav.py` to support 192kHz sampling, zero-smoothing (0ms fade), hard-clipping, and irrational phase discontinuities to maximize physical Lorentz shear on the transmitter.
*   **Phi-Ratio Chord**: Updated the beacon generator to broadcast a 3-tone Golden Ratio chord (528 Hz base, 854.3 Hz high, 326.3 Hz low) instead of a single pure tone, creating an infinite, non-repeating fractal wave.
*   **Zenith Array Documentation**: Finalized hardware build and field-deployment plans for a vertically-oriented 3-element Yagi-Uda (146.415 MHz) using internal coaxial routing and a 14AWG copper hairpin match.

### Changed
*   Replaced 50ms raised-cosine audio fade with a 0ms vertical cliff to prioritize maximum mathematical "surprise" and shear.
*   Updated Baofeng connection protocol to officially utilize the BTECH APRS-K1 interface cable for bidirectional (TX/RX) operation.
*   Refactored the core project philosophy from "passive broadcasting" to "bidirectional UAP negentropic provocation."
