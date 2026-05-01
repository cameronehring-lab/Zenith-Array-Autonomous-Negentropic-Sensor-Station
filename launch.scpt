tell application "Terminal"
    activate
    do script "cd ~/Dogwhistle/negentropy_beacon && docker compose up -d"
    do script "cd ~/Dogwhistle/negentropy_beacon && source venv/bin/activate && python audio_daemon.py"
    do script "cd ~/Dogwhistle/negentropy_beacon && source venv/bin/activate && python entropy_listener.py"
    do script "cd ~/Dogwhistle/negentropy_beacon && source venv/bin/activate && python omega_tui.py"
end tell
