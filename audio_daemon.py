import json
import redis
from worker import execute_prime_sequence

def main():
    r = redis.Redis(host='localhost', port=6380)
    print("==================================================")
    print("  OMEGA4 CoreAudio Hardware Daemon")
    print("  Bypassing OS Fork to protect Apple Silicon")
    print("  Status: ACTIVE")
    print("==================================================")
    
    while True:
        # Block until a job arrives in the queue
        _, data = r.brpop('hardware_queue')
        job = json.loads(data)
        
        print(f"\n[>>] Payload Received: {job['action']}")
        try:
            if job['action'] == 'execute_prime_sequence':
                execute_prime_sequence(*job['args'])
                print("[✓] Transmission Complete.")
        except Exception as e:
            print(f"[!] Hardware Error: {e}")

if __name__ == "__main__":
    main()
