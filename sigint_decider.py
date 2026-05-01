import subprocess
import datetime
import os
import redis

# --- Apple Silicon Paths (Scoped to Project Directory) ---
SATDUMP_BIN = "/usr/local/bin/satdump" # Typical install path

def get_output_dir():
    try:
        r = redis.Redis(host='localhost', port=6380)
        session_dir = r.get('current_session_dir')
        if session_dir:
            path = os.path.join(session_dir.decode('utf-8'), "images")
            os.makedirs(path, exist_ok=True)
            return path
    except Exception:
        pass
    # Fallback if UI is not running
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "sigint", "captures")
    os.makedirs(path, exist_ok=True)
    return path

def capture_and_reconstruct(sat_name="METEOR-M2-3", freq="137.1M"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = get_output_dir()
    raw_file = os.path.join(output_dir, f"{sat_name}_{timestamp}.bin")
    
    print(f"[*] Initializing Capture on Apple Silicon: {sat_name}")
    
    # Capture raw IQ data
    # Note: 'rtl_sdr' is installed via 'brew install librtlsdr'
    subprocess.run([
        "rtl_sdr", "-f", freq, "-s", "1.024M", 
        "-g", "45", "-n", "614400000", # Approx 10 mins
        raw_file
    ])

    print(f"[*] Reconstructing imagery for {sat_name}...")
    
    # Fix the macOS dynamic library linking issue by specifying the library path
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = "/usr/local/lib"
    
    subprocess.run([
        SATDUMP_BIN, "meteor_m2-x_lrpt_72k", "baseband", 
        raw_file, f"{raw_file}_reconstructed", 
        "--samplerate", "1024000", "--format", "u8"
    ], env=env)

if __name__ == "__main__":
    capture_and_reconstruct()
