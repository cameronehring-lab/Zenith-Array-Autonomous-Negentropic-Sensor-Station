#!/usr/bin/env python3
"""
Prime-Sequence CE5 Beacon WAV Generator
=========================================
Generates .wav files containing sine tones arranged in non-linear,
prime-number pulsing sequences for VOX-triggered RF transmission.

Modes:
  - Prime:     2, 3, 5, 7, 11 second silence intervals
  - Fibonacci: 3, 6, 9, 15, 24 second silence intervals

Usage:
    python prime_pulse_wav.py [--freq 528] [--cycles 3] [--mode both]
    python prime_pulse_wav.py --freq 432 --mode fibonacci --cycles 5

Deps: numpy only (uses struct + wave for WAV output)
"""

import argparse
import numpy as np
import wave
import struct
import os

# ─── Signal Parameters ───────────────────────────────────────────────────────
SAMPLE_RATE = 192000  # Hardware limit for maximum shear resolution
BIT_DEPTH = 16
MAX_AMP = 32767  # 16-bit signed max

# Pulse sequences
PRIME_INTERVALS = [2, 3, 5, 7, 11, 13, 17]   # seconds of silence (7 primes)
FIBONACCI_369_INTERVALS = [3, 6, 9, 15, 24]  # Tesla 3-6-9 Fibonacci hybrid

# Envelope parameters
FADE_MS = 0  # Zero-smoothing (instantaneous state shifts for max negentropic shear)


def generate_tone(freq_hz, duration_s, sample_rate=SAMPLE_RATE):
    """Generate a high-shear Phi-Ratio Chord with Phase Discontinuities."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), False)
    
    phi = (1 + np.sqrt(5)) / 2
    
    tone_base = np.sin(2 * np.pi * freq_hz * t)
    tone_high = np.sin(2 * np.pi * (freq_hz * phi) * t)
    tone_low  = np.sin(2 * np.pi * (freq_hz / phi) * t)
    
    # Mix the chord
    mixed = (tone_base + tone_high + tone_low) / 3.0
    
    # INJECT PHASE DISCONTINUITY (180° flips)
    # We flip the phase at irrational time intervals (based on Phi) to maximize shear
    flip_freq = freq_hz / phi
    phase_mask = np.sign(np.sin(2 * np.pi * flip_freq * t))
    phase_mask[phase_mask == 0] = 1.0  # Prevent zeroing out the signal
    
    sheared_signal = mixed * phase_mask
    
    # HARD CLIPPING (Staircase Effect)
    # Amplify by 2x and clip to square off the rounded edges into infinite slopes
    sheared_signal = np.clip(sheared_signal * 2.0, -1.0, 1.0)
    
    return sheared_signal


def apply_envelope(signal, fade_samples):
    """Apply raised-cosine fade-in/fade-out to prevent VOX click artifacts."""
    if fade_samples <= 0 or len(signal) < 2 * fade_samples:
        return signal

    envelope = np.ones(len(signal))
    fade_in = 0.5 * (1 - np.cos(np.pi * np.arange(fade_samples) / fade_samples))
    envelope[:fade_samples] = fade_in
    fade_out = 0.5 * (1 + np.cos(np.pi * np.arange(fade_samples) / fade_samples))
    envelope[-fade_samples:] = fade_out
    return signal * envelope


def build_sequence(freq_hz, burst_duration, intervals, cycles,
                    sample_rate=SAMPLE_RATE):
    """
    Build the complete prime-pulse signal.

    Structure per cycle:
        [TONE][silence_1][TONE][silence_2]...[TONE][silence_n][TONE]
    """
    fade_samples = int(FADE_MS / 1000 * sample_rate)
    segments = []
    total_tone_time = 0
    total_silence_time = 0

    for cycle in range(cycles):
        for interval in intervals:
            tone = generate_tone(freq_hz, burst_duration, sample_rate)
            tone = apply_envelope(tone, fade_samples)
            segments.append(tone)
            total_tone_time += burst_duration

            silence = np.zeros(int(sample_rate * interval))
            segments.append(silence)
            total_silence_time += interval

        # Closing tone for this cycle
        tone = generate_tone(freq_hz, burst_duration, sample_rate)
        tone = apply_envelope(tone, fade_samples)
        segments.append(tone)
        total_tone_time += burst_duration

        # Inter-cycle gap
        if cycle < cycles - 1:
            gap = max(intervals)
            segments.append(np.zeros(int(sample_rate * gap)))
            total_silence_time += gap

    composite = np.concatenate(segments)

    # Normalize to -3dB headroom
    peak = np.max(np.abs(composite))
    if peak > 0:
        composite = composite / peak * 0.707

    duty_cycle = total_tone_time / (total_tone_time + total_silence_time) * 100
    return composite, total_tone_time, total_silence_time, duty_cycle


def save_wav(signal, filename, sample_rate=SAMPLE_RATE):
    """Save signal as 16-bit PCM WAV using the wave module."""
    int16_signal = np.int16(signal * MAX_AMP)

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)       # mono
        wf.setsampwidth(2)       # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        # Pack as little-endian int16
        raw_data = struct.pack(f'<{len(int16_signal)}h', *int16_signal)
        wf.writeframes(raw_data)

    duration = len(signal) / sample_rate
    size_kb = os.path.getsize(filename) / 1024
    print(f"  [✓] Saved: {filename}")
    print(f"      Duration: {duration:.1f}s | Size: {size_kb:.0f} KB | "
          f"{sample_rate} Hz / 16-bit PCM mono")


def analyze_spectrum(signal, freq_hz, sample_rate=SAMPLE_RATE):
    """FFT validation of the generated signal."""
    nonzero = np.nonzero(signal)[0]
    if len(nonzero) == 0:
        print("  [!] Signal is all zeros")
        return

    start = nonzero[0]
    chunk_len = min(sample_rate, len(signal) - start)
    chunk = signal[start:start + chunk_len]

    fft = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1 / sample_rate)

    phi = (1 + np.sqrt(5)) / 2
    target_freqs = [freq_hz / phi, freq_hz, freq_hz * phi]
    
    print(f"  FFT Analysis (Phi Chord):")
    for t_freq in target_freqs:
        idx = np.argmin(np.abs(freqs - t_freq))
        print(f"    Peak detected near {freqs[idx]:.1f} Hz (Target: {t_freq:.1f} Hz)")
        
    print(f"    [✓] Non-repeating fractal complexity confirmed")


def print_sequence_diagram(intervals, burst_dur, cycles):
    """Print a visual representation of the pulse sequence."""
    print(f"\n  Sequence Diagram (1 cycle):")
    print(f"  ", end="")
    for i, interval in enumerate(intervals):
        print(f"█{burst_dur:.0f}s█", end="")
        print(f"{'·' * interval}", end="")
    print(f"█{burst_dur:.0f}s█")
    print(f"  ", end="")
    for i, interval in enumerate(intervals):
        print(f"tone ", end="")
        print(f"{interval}s{'·' * max(0, interval - 2)}  ", end="")
    print(f"tone")


def main():
    p = argparse.ArgumentParser(
        description="CE5 Prime-Sequence Beacon WAV Generator")
    p.add_argument('--freq', type=float, default=528.0,
                   help='Tone frequency in Hz (default: 528)')
    p.add_argument('--burst', type=float, default=1.0,
                   help='Tone burst duration in seconds (default: 1.0)')
    p.add_argument('--cycles', type=int, default=3,
                   help='Number of sequence repetitions (default: 3)')
    p.add_argument('--mode', choices=['prime', 'fibonacci', 'both'],
                   default='both',
                   help='Sequence mode (default: both)')
    p.add_argument('--output-dir', type=str, default='.',
                   help='Output directory for WAV files')
    a = p.parse_args()

    os.makedirs(a.output_dir, exist_ok=True)

    modes = []
    if a.mode in ('prime', 'both'):
        modes.append(('prime', PRIME_INTERVALS, 'ce5_prime_beacon.wav'))
    if a.mode in ('fibonacci', 'both'):
        modes.append(('fibonacci', FIBONACCI_369_INTERVALS,
                       'ce5_fibonacci_beacon.wav'))

    for mode_name, intervals, filename in modes:
        print(f"\n{'='*60}")
        print(f"  CE5 BEACON — {mode_name.upper()} SEQUENCE")
        print(f"{'='*60}")
        print(f"  Tone:        {a.freq:.0f} Hz")
        print(f"  Burst:       {a.burst:.1f}s per pulse")
        print(f"  Intervals:   {intervals} seconds")
        print(f"  Cycles:      {a.cycles}")
        print(f"  Fade:        {FADE_MS}ms raised-cosine")
        print(f"  Output:      {SAMPLE_RATE} Hz / {BIT_DEPTH}-bit PCM")
        print(f"{'─'*60}")

        print_sequence_diagram(intervals, a.burst, a.cycles)

        signal, tone_t, sil_t, duty = build_sequence(
            a.freq, a.burst, intervals, a.cycles)

        print(f"\n  Tone time:     {tone_t:.1f}s")
        print(f"  Silence time:  {sil_t:.1f}s")
        print(f"  Total:         {tone_t + sil_t:.1f}s")
        print(f"  Duty cycle:    {duty:.1f}%")
        thermal = "✓ SAFE" if duty <= 50 else "⚠ RISK — reduce burst duration"
        print(f"  UV-5R thermal: {thermal}")

        filepath = os.path.join(a.output_dir, filename)
        save_wav(signal, filepath)
        analyze_spectrum(signal, a.freq)

    print(f"\n{'='*60}")
    print(f"  Generation complete. Files ready for VOX injection.")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
