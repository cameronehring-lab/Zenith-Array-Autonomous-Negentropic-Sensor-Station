from audio_engine import broadcast_composite, broadcast_prime_sequence
from database import log_transmission
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_payload(frequencies: list, duration: float):
    """
    Worker task: Logs intent, commands the audio hardware, and logs completion.
    Running this in the RQ worker prevents audio thread blocking on the API.
    """
    logger.info(f"Initiating payload. Frequencies: {frequencies}, Duration: {duration}s")
    
    try:
        # Log start
        log_transmission(frequencies, duration, "initiated")
        
        # Execute hardware broadcast
        broadcast_composite(frequencies, duration)
        
        # Log successful completion
        log_transmission(frequencies, duration, "completed")
        logger.info("Payload transmission complete.")
        
    except Exception as e:
        logger.error(f"Transmission failed: {e}")
        log_transmission(frequencies, duration, f"failed: {str(e)}")

def execute_prime_sequence(tone_hz: float, burst_duration: float,
                            cycles: int, mode: str):
    """
    Worker task: CE5 Prime-Sequence Beacon transmission.
    Logs the sequence parameters and executes via CoreAudio.
    """
    logger.info(f"CE5 Beacon: {tone_hz} Hz, {mode} mode, {cycles} cycles")

    try:
        log_transmission([tone_hz], burst_duration, f"ce5_{mode}_initiated")

        broadcast_prime_sequence(tone_hz, burst_duration, cycles, mode)

        log_transmission([tone_hz], burst_duration, f"ce5_{mode}_completed")
        logger.info(f"CE5 {mode} beacon sequence complete.")

    except Exception as e:
        logger.error(f"CE5 transmission failed: {e}")
        log_transmission([tone_hz], burst_duration, f"ce5_{mode}_failed: {str(e)}")

