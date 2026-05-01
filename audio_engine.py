import numpy as np
import sounddevice as sd
import time
import redis

def _abortable_wait(duration):
    """Custom wait loop that can be interrupted via Redis."""
    try:
        r = redis.Redis(host='localhost', port=6380)
        # Clear any lingering abort flags BEFORE starting the wait loop
        r.set('abort_transmission', '0') 
        start = time.time()
        while time.time() - start < duration:
            if r.get('abort_transmission') == b'1':
                sd.stop()
                r.set('abort_transmission', '0')
                break
            time.sleep(0.1)
    except Exception:
        sd.wait()


# ─── Pulse Sequences ────────────────────────────────────────────────────────
PRIME_INTERVALS = [2, 3, 5, 7, 11, 13, 17]
FIBONACCI_369_INTERVALS = [3, 6, 9, 15, 24]
FADE_MS = 50  # raised-cosine fade (ms) — prevents RF splatter

def generate_pure_tone(freq: float, duration: float, sample_rate: int = 48000) -> np.ndarray:
    """Generates a mathematically perfect floating-point sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    return np.sin(freq * t * 2 * np.pi)

def broadcast_composite(frequencies: list, duration: float):
    """
    Sums multiple frequencies into a composite wave, normalizes to prevent 
    clipping, and pushes the physical voltage to the CoreAudio hardware.
    """
    sample_rate = 48000
    waves = [generate_pure_tone(f, duration, sample_rate) for f in frequencies]
    
    # Sum and normalize the composite signal
    composite = sum(waves) / len(waves)
    
    # Push to M4 CoreAudio hardware (Triggers TRRS -> VOX)
    sd.play(composite, sample_rate)
    _abortable_wait(len(composite) / sample_rate)

def _apply_envelope(signal: np.ndarray, fade_samples: int) -> np.ndarray:
    """Raised-cosine fade-in/fade-out to prevent VOX click artifacts."""
    if len(signal) < 2 * fade_samples:
        return signal
    env = np.ones(len(signal))
    env[:fade_samples] = 0.5 * (1 - np.cos(np.pi * np.arange(fade_samples) / fade_samples))
    env[-fade_samples:] = 0.5 * (1 + np.cos(np.pi * np.arange(fade_samples) / fade_samples))
    return signal * env

def broadcast_prime_sequence(tone_hz: float = 528.0, burst_duration: float = 1.0,
                              cycles: int = 3, mode: str = 'prime'):
    """
    Generates and broadcasts a prime-number pulsed tone sequence in real-time.
    
    Args:
        tone_hz: Frequency of the tone burst (528 Hz or 432 Hz).
        burst_duration: Duration of each tone pulse in seconds.
        cycles: Number of full sequence repetitions.
        mode: 'prime' for [2,3,5,7,11] or 'fibonacci' for [3,6,9,15,24].
    """
    sample_rate = 48000
    fade_samples = int(FADE_MS / 1000 * sample_rate)
    intervals = PRIME_INTERVALS if mode == 'prime' else FIBONACCI_369_INTERVALS

    segments = []
    for _ in range(cycles):
        for interval in intervals:
            tone = generate_pure_tone(tone_hz, burst_duration, sample_rate)
            tone = _apply_envelope(tone, fade_samples)
            segments.append(tone)
            segments.append(np.zeros(int(sample_rate * interval)))
        # Closing tone
        tone = generate_pure_tone(tone_hz, burst_duration, sample_rate)
        tone = _apply_envelope(tone, fade_samples)
        segments.append(tone)

    composite = np.concatenate(segments)
    composite = composite / np.max(np.abs(composite)) * 0.707  # -3dB headroom
    sd.play(composite, sample_rate)
    _abortable_wait(len(composite) / sample_rate)

