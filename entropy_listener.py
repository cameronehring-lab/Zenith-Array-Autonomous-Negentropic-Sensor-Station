import numpy as np
import sounddevice as sd
import wave
import struct
import time
import redis
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ─── Sensor Parameters ──────────────────────────────────────────
SAMPLE_RATE = 48000
CHUNK_DURATION = 0.5  # Analyze in 0.5-second blocks
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)

# ─── Negentropy Tuning ──────────────────────────────────────────
VOLUME_SQUELCH = 0.01      # Ignore pure silence / deep background hiss
ENTROPY_THRESHOLD = 0.3    # 1.0 = Static. 0.6 = Voices. < 0.3 = Mathematically pure signals
PRE_BUFFER_CHUNKS = 4      # Keep the last 2 seconds in memory to catch the start of the signal

# ─── Telemetry Engine ───────────────────────────────────────────
try:
    telemetry_redis = redis.Redis(host='localhost', port=6380)
except Exception:
    telemetry_redis = None

try:
    influx_client = InfluxDBClient(url="http://localhost:8086", token="adminpassword", org="research")
    influx_write_api = influx_client.write_api(write_options=SYNCHRONOUS)
except Exception:
    influx_write_api = None

buffer = []
recording = False
record_buffer = []

def get_dominant_frequency(signal_chunk, sample_rate):
    """Finds the strongest frequency component in the audio chunk."""
    fft_vals = np.abs(np.fft.rfft(signal_chunk))
    freqs = np.fft.rfftfreq(len(signal_chunk), 1.0 / sample_rate)
    # Ignore DC offset and sub-bass rumble (<20Hz)
    bin_20hz = int(20 * len(signal_chunk) / sample_rate)
    if bin_20hz < len(fft_vals):
        fft_vals[:bin_20hz] = 0
    max_idx = np.argmax(fft_vals)
    return freqs[max_idx]

def calculate_spectral_entropy(signal_chunk):
    """Calculates the normalized Shannon entropy of the signal's frequency spectrum."""
    # Compute power spectrum via FFT
    fft_vals = np.abs(np.fft.rfft(signal_chunk)) ** 2
    
    # Normalize to create a probability distribution
    fft_sum = np.sum(fft_vals)
    if fft_sum == 0:
        return 1.0  # Zero signal = max entropy baseline
        
    p = fft_vals / fft_sum
    p = p[p > 0]  # Remove zeros to prevent log2(0) error
    
    # Calculate Shannon entropy: -sum(p * log2(p))
    ent = -np.sum(p * np.log2(p))
    
    # Normalize between 0 (pure tone) and 1 (pure white noise)
    max_entropy = np.log2(len(fft_vals))
    return ent / max_entropy if max_entropy > 0 else 0.0

def audio_callback(indata, frames, time_info, status):
    global buffer, recording, record_buffer
    
    if status:
        print(f"Status: {status}")
        
    # Flatten audio chunk to 1D array
    chunk = indata[:, 0].copy()
    
    # Maintain rolling pre-buffer
    buffer.append(chunk)
    if len(buffer) > PRE_BUFFER_CHUNKS:
        buffer.pop(0)
        
    volume = np.max(np.abs(chunk))
    
    # Always calculate metrics for the live data feed
    spec_entropy = calculate_spectral_entropy(chunk)
    dom_freq = get_dominant_frequency(chunk, SAMPLE_RATE)
    
    # Push live telemetry to Redis 10x a second
    manual_override = False
    if telemetry_redis:
        try:
            telemetry_redis.set('sensor_volume', float(volume))
            telemetry_redis.set('sensor_entropy', float(spec_entropy))
            telemetry_redis.set('dominant_freq', float(dom_freq))
            
            # Check for manual recording flag from TUI
            mr = telemetry_redis.get('manual_record')
            if mr and int(mr) == 1:
                manual_override = True
        except Exception:
            pass
            
    # Push to permanent InfluxDB storage for viewing
    if influx_write_api:
        try:
            point = Point("rf_sensor") \
                .tag("station", "zenith_array") \
                .field("volume", float(volume)) \
                .field("entropy", float(spec_entropy)) \
                .field("dominant_freq", float(dom_freq)) \
                .time(time.time_ns(), WritePrecision.NS)
            influx_write_api.write("transmissions", "research", point)
        except Exception:
            pass
            
    # MIRROR PROTOCOL: Autonomous Closed-Loop Response
    if telemetry_redis:
        try:
            mp = telemetry_redis.get('mirror_protocol_active')
            if mp and int(mp) == 1 and volume > VOLUME_SQUELCH:
                targets = [528.0, 1420.0, 1618.0, 854.3, 326.3]
                match = next((t for t in targets if abs(dom_freq - t) < 5.0), None)
                if match:
                    print(f"\n[⇌] MIRROR PROTOCOL ENGAGED: Matched {match}Hz. Auto-Queueing Response...")
                    import json
                    # Dispatch a 1-cycle burst of the exact matched frequency to the Hardware Daemon
                    payload = {"action": "execute_prime_sequence", "args": [match, 0.5, 1, 'prime']}
                    telemetry_redis.lpush('hardware_queue', json.dumps(payload))
                    # Suspend listening for 2 seconds to prevent audio feedback loop during transmission
                    time.sleep(2)
        except Exception:
            pass

    # Trigger recording ONLY if Manual Override is ON
    trigger_active = manual_override
    
    if trigger_active:
        if not recording:
            print(f"\n[!] CAPTURE INITIATED: MANUAL OVERRIDE")
            recording = True
            record_buffer = buffer.copy()
        else:
            record_buffer.append(chunk)
    else:
        # If we were recording and manual is turned off, save it
        if recording:
            print(f"[*] Manual override ended. Saving capture...")
            save_capture()
            recording = False

def save_capture():
    global record_buffer
    if not record_buffer:
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_negentropic_{timestamp}.wav"
    
    # Stitch chunks together
    full_audio = np.concatenate(record_buffer)
    
    # Convert float32 [-1.0, 1.0] to int16
    int16_audio = np.int16(full_audio * 32767)
    
    # Save to disk as 16-bit PCM WAV
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        raw_data = struct.pack(f'<{len(int16_audio)}h', *int16_audio)
        wf.writeframes(raw_data)
        
    print(f"  [✓] Audio saved to {filename}\n")
    record_buffer = []

def main():
    print("======================================================")
    print("  OMEGA4 Autonomous Negentropic Sensor Station")
    print("  Status: ACTIVE")
    print("  Listening for structural RF anomalies...")
    print("======================================================")

    # Start continuous non-blocking input stream
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=audio_callback, blocksize=CHUNK_SAMPLES):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping sensor station.")
            if recording:
                save_capture()

if __name__ == '__main__':
    main()
