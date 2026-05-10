from __future__ import annotations

import argparse
import audioop
import sys
import wave
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.asr_service import RealtimeChunkPolicy, decide_chunk_processing


@dataclass
class AudioAnalysisResult:
    label: str
    path: Path
    gain: float
    duration_seconds: float
    process_count: int
    drop_count: int
    waiting_count: int
    process_reasons: Counter
    drop_reasons: Counter
    gate_reasons: Counter
    tail_gate_reasons: Counter


def load_wav_as_mono_pcm16(path: Path, target_rate: int = 16000) -> bytes:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    if sample_width != 2:
        raw = audioop.lin2lin(raw, sample_width, 2)
        sample_width = 2

    if channels > 1:
        raw = audioop.tomono(raw, sample_width, 0.5, 0.5)
        channels = 1

    if sample_rate != target_rate:
        raw, _ = audioop.ratecv(raw, sample_width, channels, sample_rate, target_rate, None)

    return raw


def apply_gain(pcm: bytes, gain: float) -> bytes:
    if gain == 1.0:
        return pcm
    return audioop.mul(pcm, 2, gain)


def analyze_file(path: Path, policy: RealtimeChunkPolicy, packet_samples: int, *, gain: float = 1.0) -> AudioAnalysisResult:
    pcm = load_wav_as_mono_pcm16(path, target_rate=policy.sample_rate)
    pcm = apply_gain(pcm, gain)
    packet_bytes = packet_samples * policy.bytes_per_sample
    buffer = bytearray()
    process_reasons: Counter = Counter()
    drop_reasons: Counter = Counter()
    gate_reasons: Counter = Counter()
    tail_gate_reasons: Counter = Counter()
    process_count = 0
    drop_count = 0
    waiting_count = 0

    for i in range(0, len(pcm), packet_bytes):
        buffer.extend(pcm[i : i + packet_bytes])
        decision = decide_chunk_processing(bytes(buffer), policy)
        gate_reasons[decision.speech_gate_reason or "-"] += 1
        tail_gate_reasons[decision.tail_gate_reason or "-"] += 1

        if decision.should_process:
            process_count += 1
            process_reasons[decision.reason] += 1
            buffer.clear()
            continue

        if decision.drop_buffer:
            drop_count += 1
            drop_reasons[decision.reason] += 1
            buffer.clear()
            continue

        waiting_count += 1

    return AudioAnalysisResult(
        label=f"{path.name} @ gain={gain:.2f}",
        path=path,
        gain=gain,
        duration_seconds=len(pcm) / float(policy.sample_rate * policy.bytes_per_sample),
        process_count=process_count,
        drop_count=drop_count,
        waiting_count=waiting_count,
        process_reasons=process_reasons,
        drop_reasons=drop_reasons,
        gate_reasons=gate_reasons,
        tail_gate_reasons=tail_gate_reasons,
    )


def format_counter(counter: Counter) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}:{value}" for key, value in counter.most_common())


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline replay wav files and inspect realtime chunk policy behavior.")
    parser.add_argument("paths", nargs="+", help="Wav file paths to analyze")
    parser.add_argument("--packet-samples", type=int, default=512, help="Simulated frontend packet size in samples (default: 512)")
    parser.add_argument(
        "--gains",
        nargs="+",
        type=float,
        default=[1.0],
        help="Optional gain multipliers to replay, e.g. --gains 1.0 0.5 0.25",
    )
    args = parser.parse_args()

    policy = RealtimeChunkPolicy()
    for raw_path in args.paths:
        path = Path(raw_path).expanduser().resolve()
        for gain in args.gains:
            result = analyze_file(path, policy, packet_samples=args.packet_samples, gain=gain)
            print(f"=== {result.label} ===")
            print(f"duration_seconds={result.duration_seconds:.2f}")
            print(f"process_count={result.process_count} drop_count={result.drop_count} waiting_count={result.waiting_count}")
            print(f"process_reasons={format_counter(result.process_reasons)}")
            print(f"drop_reasons={format_counter(result.drop_reasons)}")
            print(f"speech_gate_reasons={format_counter(result.gate_reasons)}")
            print(f"tail_gate_reasons={format_counter(result.tail_gate_reasons)}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
