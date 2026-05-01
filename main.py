from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from worker import execute_payload, execute_prime_sequence

app = FastAPI(title="Negentropy Beacon Node")

# Connect to Redis container for task queuing (ISOLATED from Ghost on 6380)
redis_conn = Redis(host='localhost', port=6380)
task_queue = Queue('transmissions', connection=redis_conn)

class TransmissionRequest(BaseModel):
    frequencies: list[float]
    duration_seconds: float

class CE5Request(BaseModel):
    tone_hz: float = 528.0
    burst_duration: float = 1.0
    cycles: int = 3
    mode: str = 'prime'  # 'prime' or 'fibonacci'

@app.post("/transmit/custom")
async def queue_custom_transmission(request: TransmissionRequest):
    """
    Endpoint for programmatic array injection.
    Queues the audio sequence via Redis to prevent wave collision.
    """
    if not request.frequencies:
        raise HTTPException(status_code=400, detail="Frequency array cannot be empty")
        
    job = task_queue.enqueue(
        execute_payload, 
        request.frequencies, 
        request.duration_seconds
    )
    
    return {
        "status": "queued",
        "job_id": job.get_id(),
        "payload": request.dict()
    }

@app.post("/transmit/negentropy")
async def queue_negentropy_baseline(duration_seconds: float = 5.0):
    """
    Standardized payload: 1420 Hz (Hydrogen) + 1618 Hz (Phi).
    """
    frequencies = [1420.0, 1618.0]
    
    job = task_queue.enqueue(
        execute_payload, 
        frequencies, 
        duration_seconds
    )
    
    return {
        "status": "queued",
        "job_id": job.get_id(),
        "payload": {
            "frequencies": frequencies,
            "duration_seconds": duration_seconds
        }
    }

@app.post("/transmit/ce5-prime")
async def queue_ce5_prime(request: CE5Request):
    """
    CE5 Prime-Sequence Beacon.
    Transmits tone pulses at prime-number intervals (2,3,5,7,11)
    or Fibonacci 3-6-9 intervals (3,6,9,15,24).
    Enforces 50% duty cycle to protect UV-5R thermals.
    """
    if request.mode not in ('prime', 'fibonacci'):
        raise HTTPException(status_code=400,
                            detail="Mode must be 'prime' or 'fibonacci'")

    job = task_queue.enqueue(
        execute_prime_sequence,
        request.tone_hz,
        request.burst_duration,
        request.cycles,
        request.mode
    )

    return {
        "status": "queued",
        "job_id": job.get_id(),
        "payload": request.dict()
    }

