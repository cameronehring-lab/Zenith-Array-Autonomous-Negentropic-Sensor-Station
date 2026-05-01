import time
import random
from database import log_transmission, write_api

print("Generating synthetic negentropy test patterns to InfluxDB...")

# 1. Simulate 5 random noise transmissions (representing baseline RF interference/chaff)
print("Injecting baseline RF noise...")
for _ in range(5):
    noise_freqs = [random.uniform(462.0, 467.0) for _ in range(random.randint(2, 6))]
    log_transmission(noise_freqs, random.uniform(0.5, 2.5), "baseline_noise")
    time.sleep(0.5)

# 2. Simulate the deliberate Negentropy Payload (The Dogwhistle Anomaly)
print("Injecting structured UAP Dogwhistle payload anomaly...")
# 1420.0 Hz (Hydrogen) + 1618.0 Hz (Golden Ratio Phi)
negentropy_payload = [1420.0, 1618.0]
for _ in range(3):
    log_transmission(negentropy_payload, 5.0, "initiated")
    time.sleep(1)
    log_transmission(negentropy_payload, 5.0, "completed")
    time.sleep(1)

# Ensure the write buffer pushes to Docker
write_api.flush()
print("Data injection complete! The ledger holds 11 anomalous records.")
