import curses
import time
import json
import os
from datetime import datetime
from redis import Redis

# Session Logging Setup
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_DIR = f"sessions/session_{SESSION_ID}"
os.makedirs(f"{SESSION_DIR}/images", exist_ok=True)
os.makedirs(f"{SESSION_DIR}/data", exist_ok=True)
SESSION_FILE = f"{SESSION_DIR}/events.log"

# Connect to Redis
try:
    redis_conn = Redis(host='localhost', port=6380)
    redis_conn.ping()
    # Publish the current active session path so external scripts (like sigint) can use it
    redis_conn.set('current_session_dir', SESSION_DIR)
except Exception:
    redis_conn = None

logs = ["[SYS] ZENITH ARRAY Terminal Interface Initialized.", f"[SYS] SESSION DIR: {SESSION_DIR}"]

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    logs.append(full_msg)
    if len(logs) > 15:
        logs.pop(0)
        
    try:
        with open(SESSION_FILE, "a") as f:
            f.write(full_msg + "\n")
    except Exception:
        pass

def draw_tui(stdscr):
    # Setup Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.curs_set(0)
    stdscr.nodelay(1)
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # 1. Header
        stdscr.addstr(1, 2, " ZENITH ARRAY COMMAND TERMINAL ", curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
        stdscr.addstr(2, 2, " Autonomous Negentropy Beacon ", curses.color_pair(2))
        
        # 2. Status Panel
        try:
            # Ping redis to check status
            redis_conn.ping()
            q_len = redis_conn.llen('hardware_queue')
            r_stat = "ACTIVE"
        except Exception:
            q_len = 0
            r_stat = "OFFLINE"
            
        stdscr.addstr(4, 2, "REDIS STATUS : ", curses.color_pair(2))
        if r_stat == "ACTIVE":
            stdscr.addstr(r_stat, curses.color_pair(1) | curses.A_BOLD)
        else:
            stdscr.addstr(r_stat, curses.color_pair(3) | curses.A_BOLD)
            
        stdscr.addstr(5, 2, f"QUEUE LENGTH : {q_len}", curses.color_pair(2))
        stdscr.addstr(6, 2, "LORENTZ SHEAR: 192kHz (MAX)", curses.color_pair(1))
        
        # 3. Controls Panel
        stdscr.addstr(7, 2, "─── HARDWARE CONTROLS ────────────", curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(8, 2, "[P] PRIME (528)    | [S] Toggle SKY SONAR")
        stdscr.addstr(9, 2, "[H] HYDROGEN(1420) | [M] Toggle MIRROR PROTOCOL")
        stdscr.addstr(10, 2, "[F] FIBONACCI      | [X] ABORT TRANSMISSION")
        stdscr.addstr(11, 2, "[R] Toggle RECORD  | [L] Manual Log")
        stdscr.addstr(12, 2, "[Q] Shutdown Term  |")
        
        # 4. Live Sensor Feed
        try:
            vol = float(redis_conn.get('sensor_volume') or 0.0)
            ent = float(redis_conn.get('sensor_entropy') or 1.0)
            dom_freq = float(redis_conn.get('sensor_dom_freq') or 0.0)
            is_recording = (redis_conn.get('is_recording') == b'1')
        except Exception:
            vol = 0.0
            ent = 1.0
            dom_freq = 0.0
            is_recording = False

        stdscr.addstr(13, 2, "─── LIVE SENSOR FEED ─────────────", curses.color_pair(2) | curses.A_BOLD)
        
        # Volume ASCII Bar
        vol_bars = int((vol / 0.5) * 20) # Scale down for columns
        vol_bars = min(20, max(0, vol_bars))
        vol_display = "█" * vol_bars + "▒" * (20 - vol_bars)
        stdscr.addstr(14, 2, f"AUDIO: [{vol_display}] {vol:.3f}", curses.color_pair(1))
        
        # Entropy ASCII Bar
        ent_bars = int(ent * 20)
        ent_bars = min(20, max(0, ent_bars))
        ent_display = "█" * ent_bars + "▒" * (20 - ent_bars)
        stdscr.addstr(15, 2, f"ENTRO: [{ent_display}] {ent:.3f}", curses.color_pair(2))
        stdscr.addstr(16, 2, f"FREQ : {dom_freq:.1f} Hz", curses.color_pair(2))
        
        # Mode Status Indicators
        ss_str = redis_conn.get('sky_sonar_active')
        mp_str = redis_conn.get('mirror_protocol_active')
        if ss_str and int(ss_str) == 1:
            stdscr.addstr(17, 2, " [~] SKY SONAR ACTIVE ", curses.color_pair(3) | curses.A_REVERSE)
        if mp_str and int(mp_str) == 1:
            stdscr.addstr(18, 2, " [⇌] MIRROR PROTOCOL ARMED ", curses.color_pair(3) | curses.A_REVERSE)
        
        targets = [528.0, 1420.0, 1618.0, 854.3, 326.3]
        match = next((t for t in targets if abs(dom_freq - t) < 5.0), None)
        
        if match and vol > 0.01:
            stdscr.addstr(16, 25, f" >>> MATCH: {match} Hz <<< ", curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)
        elif ent < 0.3 and vol > 0.01:
            stdscr.addstr(16, 25, f" >>> ANOMALY DETECTED <<< ", curses.color_pair(2) | curses.A_BOLD | curses.A_REVERSE)

        if is_recording:
            stdscr.addstr(18, 35, " [REC] ", curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)

        # 5. Log Panel
        stdscr.addstr(20, 2, "─── SYSTEM LOGS ──────────────────", curses.color_pair(2) | curses.A_BOLD)
        for i, l in enumerate(logs):
            if 21 + i < height - 1:
                stdscr.addstr(21 + i, 2, l[:width-4])
                
        stdscr.refresh()
        
        # Handle Keyboard Input
        try:
            key = stdscr.getkey()
        except Exception:
            key = None
            
        if key in ('q', 'Q'):
            log("SESSION TERMINATED BY USER.")
            time.sleep(0.5)
            break
        elif key in ('p', 'P'):
            if r_stat == "ACTIVE":
                payload = {"action": "execute_prime_sequence", "args": [528.0, 1.0, 3, 'prime']}
                redis_conn.lpush('hardware_queue', json.dumps(payload))
                log(f"Queued PRIME payload.")
            else:
                log("ERROR: Redis is offline. Start docker-compose.")
        elif key in ('f', 'F'):
            if r_stat == "ACTIVE":
                payload = {"action": "execute_prime_sequence", "args": [1618.0, 0.5, 3, 'fibonacci']}
                redis_conn.lpush('hardware_queue', json.dumps(payload))
                log("Fibonacci Sequence (1618Hz) Queued.")
        elif key in ('x', 'X'):
            if r_stat == "ACTIVE":
                redis_conn.set('abort_transmission', '1')
                log(">>> ABORT SIGNAL SENT TO DAEMON <<<")
            else:
                log("ERROR: Redis is offline. Start docker-compose.")
        elif key in ('r', 'R'):
            if r_stat == "ACTIVE":
                current = redis_conn.get('manual_record')
                new_state = 0 if current and int(current) == 1 else 1
                redis_conn.set('manual_record', new_state)
                state_str = "STARTED" if new_state == 1 else "STOPPED"
                log(f"Manual Override {state_str}.")
            else:
                log("ERROR: Redis is offline. Cannot toggle recording.")
        elif key in ('l', 'L'):
            # Manual Data Entry
            stdscr.nodelay(0) # Blocking mode for input
            curses.echo()
            stdscr.addstr(height - 1, 2, "ENTER MANUAL HARDWARE READING: ", curses.color_pair(1) | curses.A_BOLD)
            try:
                user_input = stdscr.getstr(height - 1, 33, 60).decode('utf-8')
                if user_input.strip():
                    log(f"MANUAL LOG (Freq:{dom_freq:.1f}Hz, Ent:{ent:.2f}): {user_input.strip()}")
            except Exception:
                pass
            curses.noecho()
            stdscr.nodelay(1) # Back to non-blocking
            stdscr.move(height - 1, 0)
            stdscr.clrtoeol()
        elif key in ('s', 'S'):
            if r_stat == "ACTIVE":
                current = redis_conn.get('sky_sonar_active')
                new_state = 0 if current and int(current) == 1 else 1
                redis_conn.set('sky_sonar_active', new_state)
                log(f"Sky Sonar Mode {'ENABLED' if new_state == 1 else 'DISABLED'}.")
        elif key in ('m', 'M'):
            if r_stat == "ACTIVE":
                current = redis_conn.get('mirror_protocol_active')
                new_state = 0 if current and int(current) == 1 else 1
                redis_conn.set('mirror_protocol_active', new_state)
                log(f"Mirror Protocol {'ARMED' if new_state == 1 else 'DISARMED'}.")
                
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        curses.wrapper(draw_tui)
    except KeyboardInterrupt:
        pass
