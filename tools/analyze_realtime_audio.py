from __future__ import annotations

import argparse
import audioop
import sys
import wave
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.asr_service import ChunkDecision, RealtimeChunkPolicy, decide_chunk_processing, decide_stop_flush


@dataclass
class TimelineEvent:
    source: str
    action: str
    reason: str
    packet_index: int | None
    stream_start_seconds: float
    stream_end_seconds: float
    buffer_duration_seconds: float
    trailing_silence_detected: bool
    speech_gate_reason: str
    tail_gate_reason: str
    rms: float
    peak: int
    active_ratio: float
    voiced_ratio: float
    silence_ratio: float
    active_seconds: float
    voiced_seconds: float
    voiced_density: float


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
    timeline_events: list[TimelineEvent]
    stop_flush_event: TimelineEvent | None
    final_buffer_seconds: float


def format_gain(gain: float) -> str:
    return f"{gain:.4g}"


def seconds_to_pcm_bytes(
    seconds: float,
    *,
    sample_rate: int,
    bytes_per_sample: int,
) -> int:
    if seconds <= 0:
        return 0
    sample_count = int(round(seconds * sample_rate))
    return max(0, sample_count * bytes_per_sample)


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


def mix_pcm_streams(
    foreground_pcm: bytes,
    background_pcm: bytes,
    *,
    foreground_gain: float = 1.0,
    background_gain: float = 1.0,
    background_offset_seconds: float = 0.0,
    tail_silence_seconds: float = 0.0,
    sample_rate: int = 16000,
    bytes_per_sample: int = 2,
) -> bytes:
    foreground_pcm = apply_gain(foreground_pcm, foreground_gain)
    background_pcm = apply_gain(background_pcm, background_gain)

    background_offset_bytes = seconds_to_pcm_bytes(
        background_offset_seconds,
        sample_rate=sample_rate,
        bytes_per_sample=bytes_per_sample,
    )
    tail_silence_bytes = seconds_to_pcm_bytes(
        tail_silence_seconds,
        sample_rate=sample_rate,
        bytes_per_sample=bytes_per_sample,
    )

    aligned_background = (b"\x00" * background_offset_bytes) + background_pcm
    total_length = max(len(foreground_pcm), len(aligned_background)) + tail_silence_bytes
    foreground_aligned = foreground_pcm.ljust(total_length, b"\x00")
    background_aligned = aligned_background.ljust(total_length, b"\x00")
    return audioop.add(foreground_aligned, background_aligned, bytes_per_sample)


def decision_to_action(decision: ChunkDecision, *, stop_flush: bool = False) -> str:
    if decision.should_process:
        return "stop_process" if stop_flush else "process"
    if decision.drop_buffer:
        return "stop_drop" if stop_flush else "drop"
    return "stop_skip" if stop_flush else "waiting"


def build_timeline_event(
    *,
    decision: ChunkDecision,
    action: str,
    source: str,
    packet_index: int | None,
    stream_end_seconds: float,
) -> TimelineEvent:
    features = decision.audio_features
    buffer_duration_seconds = decision.audio_duration_seconds
    stream_start_seconds = max(0.0, stream_end_seconds - buffer_duration_seconds)
    return TimelineEvent(
        source=source,
        action=action,
        reason=decision.reason,
        packet_index=packet_index,
        stream_start_seconds=stream_start_seconds,
        stream_end_seconds=stream_end_seconds,
        buffer_duration_seconds=buffer_duration_seconds,
        trailing_silence_detected=decision.trailing_silence_detected,
        speech_gate_reason=decision.speech_gate_reason or "-",
        tail_gate_reason=decision.tail_gate_reason or "-",
        rms=(features.rms if features else 0.0),
        peak=(features.peak if features else 0),
        active_ratio=(features.active_ratio if features else 0.0),
        voiced_ratio=(features.voiced_ratio if features else 0.0),
        silence_ratio=(features.silence_ratio if features else 0.0),
        active_seconds=(features.active_seconds if features else 0.0),
        voiced_seconds=(features.voiced_seconds if features else 0.0),
        voiced_density=(features.voiced_density if features else 0.0),
    )


def analyze_pcm(
    pcm: bytes,
    policy: RealtimeChunkPolicy,
    packet_samples: int,
    *,
    gain: float = 1.0,
    simulate_stop_flush: bool = True,
) -> AudioAnalysisResult:
    pcm = apply_gain(pcm, gain)
    packet_bytes = packet_samples * policy.bytes_per_sample
    bytes_per_second = float(policy.sample_rate * policy.bytes_per_sample)
    buffer = bytearray()
    process_reasons: Counter = Counter()
    drop_reasons: Counter = Counter()
    gate_reasons: Counter = Counter()
    tail_gate_reasons: Counter = Counter()
    timeline_events: list[TimelineEvent] = []
    process_count = 0
    drop_count = 0
    waiting_count = 0
    bytes_consumed = 0

    for packet_index, offset in enumerate(range(0, len(pcm), packet_bytes), start=1):
        packet = pcm[offset : offset + packet_bytes]
        buffer.extend(packet)
        bytes_consumed += len(packet)
        decision = decide_chunk_processing(bytes(buffer), policy)
        gate_reasons[decision.speech_gate_reason or "-"] += 1
        tail_gate_reasons[decision.tail_gate_reason or "-"] += 1

        action = decision_to_action(decision)
        timeline_events.append(
            build_timeline_event(
                decision=decision,
                action=action,
                source="chunk",
                packet_index=packet_index,
                stream_end_seconds=bytes_consumed / bytes_per_second,
            )
        )

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

    stop_flush_event: TimelineEvent | None = None
    final_buffer_seconds = len(buffer) / bytes_per_second

    if simulate_stop_flush and buffer:
        decision = decide_stop_flush(bytes(buffer), policy)
        action = decision_to_action(decision, stop_flush=True)
        stop_flush_event = build_timeline_event(
            decision=decision,
            action=action,
            source="stop_flush",
            packet_index=None,
            stream_end_seconds=bytes_consumed / bytes_per_second,
        )
        timeline_events.append(stop_flush_event)

    return AudioAnalysisResult(
        label=f"pcm @ gain={format_gain(gain)}",
        path=Path("<pcm>"),
        gain=gain,
        duration_seconds=len(pcm) / bytes_per_second,
        process_count=process_count,
        drop_count=drop_count,
        waiting_count=waiting_count,
        process_reasons=process_reasons,
        drop_reasons=drop_reasons,
        gate_reasons=gate_reasons,
        tail_gate_reasons=tail_gate_reasons,
        timeline_events=timeline_events,
        stop_flush_event=stop_flush_event,
        final_buffer_seconds=final_buffer_seconds,
    )


def analyze_file(
    path: Path,
    policy: RealtimeChunkPolicy,
    packet_samples: int,
    *,
    gain: float = 1.0,
    simulate_stop_flush: bool = True,
) -> AudioAnalysisResult:
    pcm = load_wav_as_mono_pcm16(path, target_rate=policy.sample_rate)
    result = analyze_pcm(
        pcm,
        policy,
        packet_samples=packet_samples,
        gain=gain,
        simulate_stop_flush=simulate_stop_flush,
    )
    result.label = f"{path.name} @ gain={format_gain(gain)}"
    result.path = path
    return result


def analyze_mixed_files(
    foreground_path: Path,
    background_path: Path,
    policy: RealtimeChunkPolicy,
    packet_samples: int,
    *,
    foreground_gain: float = 1.0,
    background_gain: float = 1.0,
    background_offset_seconds: float = 0.0,
    tail_silence_seconds: float = 0.0,
    simulate_stop_flush: bool = True,
) -> AudioAnalysisResult:
    foreground_pcm = load_wav_as_mono_pcm16(foreground_path, target_rate=policy.sample_rate)
    background_pcm = load_wav_as_mono_pcm16(background_path, target_rate=policy.sample_rate)
    mixed_pcm = mix_pcm_streams(
        foreground_pcm,
        background_pcm,
        foreground_gain=foreground_gain,
        background_gain=background_gain,
        background_offset_seconds=background_offset_seconds,
        tail_silence_seconds=tail_silence_seconds,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
    )
    result = analyze_pcm(
        mixed_pcm,
        policy,
        packet_samples=packet_samples,
        gain=1.0,
        simulate_stop_flush=simulate_stop_flush,
    )
    result.label = (
        f"{foreground_path.name} @ gain={format_gain(foreground_gain)} "
        f"+ bg({background_path.name} @ {format_gain(background_gain)}, "
        f"offset={background_offset_seconds:.2f}s, tail={tail_silence_seconds:.2f}s)"
    )
    result.path = foreground_path
    return result


def format_counter(counter: Counter) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}:{value}" for key, value in counter.most_common())


def format_timeline_event(event: TimelineEvent) -> str:
    packet_label = "-" if event.packet_index is None else str(event.packet_index)
    return (
        f"[{event.source}:{packet_label}] {event.action} reason={event.reason} "
        f"window={event.stream_start_seconds:.2f}-{event.stream_end_seconds:.2f}s "
        f"buffer={event.buffer_duration_seconds:.2f}s "
        f"gate={event.speech_gate_reason} tail={event.tail_gate_reason} "
        f"silence={event.trailing_silence_detected} "
        f"rms={event.rms:.4f} peak={event.peak} "
        f"active={event.active_ratio:.2f}/{event.active_seconds:.2f}s "
        f"voiced={event.voiced_ratio:.2f}/{event.voiced_seconds:.2f}s "
        f"density={event.voiced_density:.2f} "
        f"silence_ratio={event.silence_ratio:.2f}"
    )


def select_timeline_events(
    events: Iterable[TimelineEvent],
    *,
    include_waiting: bool = False,
    limit: int = 12,
) -> list[TimelineEvent]:
    filtered = [
        event
        for event in events
        if include_waiting or event.action not in {"waiting"}
    ]
    if limit > 0 and len(filtered) > limit:
        return filtered[-limit:]
    return filtered


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
    parser.add_argument("--timeline", action="store_true", help="Print event timeline for significant chunk decisions")
    parser.add_argument(
        "--timeline-include-waiting",
        action="store_true",
        help="When printing timeline, also include waiting_for_more_audio steps",
    )
    parser.add_argument(
        "--timeline-limit",
        type=int,
        default=12,
        help="Maximum timeline rows to print when --timeline is enabled; 0 means print all",
    )
    parser.add_argument(
        "--no-stop-flush",
        action="store_true",
        help="Do not simulate the final stop-recording flush for leftover audio",
    )
    parser.add_argument(
        "--mix-background",
        help="Optional background wav to mix into every primary path for weak-background simulation",
    )
    parser.add_argument(
        "--mix-background-gains",
        nargs="+",
        type=float,
        default=[0.06],
        help="Background gain multipliers used with --mix-background (default: 0.06)",
    )
    parser.add_argument(
        "--mix-background-offset-seconds",
        type=float,
        default=0.0,
        help="Offset in seconds before the background wav starts inside the mixed scene",
    )
    parser.add_argument(
        "--mix-tail-silence-seconds",
        type=float,
        default=0.0,
        help="Optional silence appended after the mixed scene to make stop-flush / tail behavior easier to inspect",
    )
    args = parser.parse_args()

    policy = RealtimeChunkPolicy()
    background_path = Path(args.mix_background).expanduser().resolve() if args.mix_background else None
    for raw_path in args.paths:
        path = Path(raw_path).expanduser().resolve()
        if background_path:
            analysis_inputs = [
                analyze_mixed_files(
                    path,
                    background_path,
                    policy,
                    packet_samples=args.packet_samples,
                    foreground_gain=gain,
                    background_gain=background_gain,
                    background_offset_seconds=args.mix_background_offset_seconds,
                    tail_silence_seconds=args.mix_tail_silence_seconds,
                    simulate_stop_flush=not args.no_stop_flush,
                )
                for gain in args.gains
                for background_gain in args.mix_background_gains
            ]
        else:
            analysis_inputs = [
                analyze_file(
                    path,
                    policy,
                    packet_samples=args.packet_samples,
                    gain=gain,
                    simulate_stop_flush=not args.no_stop_flush,
                )
                for gain in args.gains
            ]

        for result in analysis_inputs:
            print(f"=== {result.label} ===")
            print(f"duration_seconds={result.duration_seconds:.2f}")
            print(
                f"process_count={result.process_count} "
                f"drop_count={result.drop_count} "
                f"waiting_count={result.waiting_count}"
            )
            print(f"process_reasons={format_counter(result.process_reasons)}")
            print(f"drop_reasons={format_counter(result.drop_reasons)}")
            print(f"speech_gate_reasons={format_counter(result.gate_reasons)}")
            print(f"tail_gate_reasons={format_counter(result.tail_gate_reasons)}")
            print(f"final_buffer_seconds={result.final_buffer_seconds:.2f}")
            if result.stop_flush_event:
                print(f"stop_flush={format_timeline_event(result.stop_flush_event)}")
            else:
                print("stop_flush=-")

            if args.timeline:
                timeline = select_timeline_events(
                    result.timeline_events,
                    include_waiting=args.timeline_include_waiting,
                    limit=args.timeline_limit,
                )
                hidden_count = 0
                if args.timeline_limit > 0:
                    base_filtered = select_timeline_events(
                        result.timeline_events,
                        include_waiting=args.timeline_include_waiting,
                        limit=0,
                    )
                    hidden_count = max(0, len(base_filtered) - len(timeline))
                print("timeline:")
                if hidden_count:
                    print(f"  ... hidden_events={hidden_count}")
                if not timeline:
                    print("  -")
                for event in timeline:
                    print(f"  {format_timeline_event(event)}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
