"""
Pulse interval sequence generators for the CE5 beacon protocol.
All functions return a list of n gap values (in sequence units).
"""
from typing import Literal

SequenceType = Literal["primes", "369", "fibonacci"]


def primes(n: int) -> list[int]:
    result: list[int] = []
    candidate = 2
    while len(result) < n:
        if all(candidate % p != 0 for p in result):
            result.append(candidate)
        candidate += 1
    return result


def sequence_369(n: int) -> list[int]:
    return [3 * ((i % 3) + 1) for i in range(n)]


def fibonacci(n: int) -> list[int]:
    if n == 0:
        return []
    if n == 1:
        return [1]
    seq = [1, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]


def get_sequence(kind: SequenceType, n: int) -> list[int]:
    return {"primes": primes, "369": sequence_369, "fibonacci": fibonacci}[kind](n)
