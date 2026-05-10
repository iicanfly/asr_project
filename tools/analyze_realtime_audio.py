from __future__ import annotations

import argparse
import audioop
import json
import sys
import wave
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.asr_service import (
    ChunkDecision,
    RealtimeChunkPolicy,
    build_realtime_chunk_policy,
    decide_chunk_processing,
    decide_chunk_processing_simple,
    decide_stop_flush,
    decide_stop_flush_simple,
)


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
    max_active_run_seconds: float
    max_voiced_run_seconds: float
    voiced_density: float


@dataclass
class AudioAnalysisResult:
    label: str
    path: Path
    gain: float
    scenario: dict[str, Any]
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


def load_pcm_as_mono_pcm16(
    path: Path,
    *,
    source_rate: int = 16000,
    source_channels: int = 1,
    source_sample_width: int = 2,
    target_rate: int = 16000,
) -> bytes:
    raw = path.read_bytes()
    if source_channels < 1:
        raise ValueError(f"Invalid PCM channel count: {source_channels}")
    if source_channels > 2:
        raise ValueError("PCM analyzer currently supports mono or stereo input only")

    if source_sample_width != 2:
        raw = audioop.lin2lin(raw, source_sample_width, 2)
        source_sample_width = 2

    if source_channels == 2:
        raw = audioop.tomono(raw, source_sample_width, 0.5, 0.5)
        source_channels = 1

    if source_rate != target_rate:
        raw, _ = audioop.ratecv(
            raw,
            source_sample_width,
            source_channels,
            source_rate,
            target_rate,
            None,
        )

    return raw


def detect_input_format(path: Path, requested_format: str) -> str:
    if requested_format != "auto":
        return requested_format

    suffix = path.suffix.lower()
    if suffix == ".wav":
        return "wav"
    if suffix == ".pcm":
        return "pcm"
    raise ValueError(f"Cannot auto-detect input format for: {path}")


def load_audio_as_mono_pcm16(
    path: Path,
    *,
    input_format: str = "auto",
    target_rate: int = 16000,
    pcm_sample_rate: int = 16000,
    pcm_channels: int = 1,
    pcm_sample_width: int = 2,
) -> tuple[bytes, str]:
    resolved_format = detect_input_format(path, input_format)
    if resolved_format == "wav":
        return load_wav_as_mono_pcm16(path, target_rate=target_rate), resolved_format
    if resolved_format == "pcm":
        return (
            load_pcm_as_mono_pcm16(
                path,
                source_rate=pcm_sample_rate,
                source_channels=pcm_channels,
                source_sample_width=pcm_sample_width,
                target_rate=target_rate,
            ),
            resolved_format,
        )
    raise ValueError(f"Unsupported input format: {resolved_format}")


def clip_pcm(
    pcm: bytes,
    *,
    start_seconds: float = 0.0,
    duration_seconds: float | None = None,
    sample_rate: int = 16000,
    bytes_per_sample: int = 2,
) -> bytes:
    if not pcm:
        return pcm

    start_byte = seconds_to_pcm_bytes(
        start_seconds,
        sample_rate=sample_rate,
        bytes_per_sample=bytes_per_sample,
    )
    if start_byte >= len(pcm):
        return b""

    clipped = pcm[start_byte:]
    if duration_seconds is None:
        return clipped

    clip_length_bytes = seconds_to_pcm_bytes(
        duration_seconds,
        sample_rate=sample_rate,
        bytes_per_sample=bytes_per_sample,
    )
    if clip_length_bytes <= 0:
        return b""
    return clipped[:clip_length_bytes]


def apply_gain(pcm: bytes, gain: float) -> bytes:
    if gain == 1.0:
        return pcm
    return audioop.mul(pcm, 2, gain)


def describe_clip(start_seconds: float, duration_seconds: float | None) -> str:
    if start_seconds <= 0 and duration_seconds is None:
        return ""
    if duration_seconds is None:
        return f", clip={start_seconds:.2f}s:"
    return f", clip={start_seconds:.2f}s:+{duration_seconds:.2f}s"


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
        max_active_run_seconds=(features.max_active_run_seconds if features else 0.0),
        max_voiced_run_seconds=(features.max_voiced_run_seconds if features else 0.0),
        voiced_density=(features.voiced_density if features else 0.0),
    )


def analyze_pcm(
    pcm: bytes,
    policy: RealtimeChunkPolicy,
    packet_samples: int,
    *,
    pipeline: str = "legacy",
    gain: float = 1.0,
    simulate_stop_flush: bool = True,
) -> AudioAnalysisResult:
    if pipeline == "simplified":
        decide_chunk = decide_chunk_processing_simple
        decide_stop_flush_fn = decide_stop_flush_simple
    elif pipeline == "legacy":
        decide_chunk = decide_chunk_processing
        decide_stop_flush_fn = decide_stop_flush
    else:
        raise ValueError(f"Unsupported pipeline: {pipeline}")

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
        decision = decide_chunk(bytes(buffer), policy)
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
        decision = decide_stop_flush_fn(bytes(buffer), policy)
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
        scenario={
            "mode": "pcm",
            "pipeline": pipeline,
            "gain": gain,
            "simulate_stop_flush": simulate_stop_flush,
        },
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
    input_format: str = "auto",
    pcm_sample_rate: int = 16000,
    pcm_channels: int = 1,
    pcm_sample_width: int = 2,
    pipeline: str = "legacy",
    gain: float = 1.0,
    clip_start_seconds: float = 0.0,
    clip_duration_seconds: float | None = None,
    simulate_stop_flush: bool = True,
) -> AudioAnalysisResult:
    pcm, resolved_format = load_audio_as_mono_pcm16(
        path,
        input_format=input_format,
        target_rate=policy.sample_rate,
        pcm_sample_rate=pcm_sample_rate,
        pcm_channels=pcm_channels,
        pcm_sample_width=pcm_sample_width,
    )
    pcm = clip_pcm(
        pcm,
        start_seconds=clip_start_seconds,
        duration_seconds=clip_duration_seconds,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
    )
    result = analyze_pcm(
        pcm,
        policy,
        packet_samples=packet_samples,
        pipeline=pipeline,
        gain=gain,
        simulate_stop_flush=simulate_stop_flush,
    )
    result.label = (
        f"{path.name} @ gain={format_gain(gain)}"
        f"{describe_clip(clip_start_seconds, clip_duration_seconds)}"
    )
    result.path = path
    result.scenario = {
        "mode": "single",
        "pipeline": pipeline,
        "path": str(path),
        "input_format": resolved_format,
        "gain": gain,
        "clip_start_seconds": clip_start_seconds,
        "clip_duration_seconds": clip_duration_seconds,
        "simulate_stop_flush": simulate_stop_flush,
    }
    return result


def analyze_mixed_files(
    foreground_path: Path,
    background_path: Path,
    policy: RealtimeChunkPolicy,
    packet_samples: int,
    *,
    input_format: str = "auto",
    pcm_sample_rate: int = 16000,
    pcm_channels: int = 1,
    pcm_sample_width: int = 2,
    pipeline: str = "legacy",
    foreground_gain: float = 1.0,
    background_gain: float = 1.0,
    foreground_clip_start_seconds: float = 0.0,
    foreground_clip_duration_seconds: float | None = None,
    background_clip_start_seconds: float = 0.0,
    background_clip_duration_seconds: float | None = None,
    background_offset_seconds: float = 0.0,
    tail_silence_seconds: float = 0.0,
    simulate_stop_flush: bool = True,
) -> AudioAnalysisResult:
    foreground_pcm, foreground_format = load_audio_as_mono_pcm16(
        foreground_path,
        input_format=input_format,
        target_rate=policy.sample_rate,
        pcm_sample_rate=pcm_sample_rate,
        pcm_channels=pcm_channels,
        pcm_sample_width=pcm_sample_width,
    )
    background_pcm, background_format = load_audio_as_mono_pcm16(
        background_path,
        input_format=input_format,
        target_rate=policy.sample_rate,
        pcm_sample_rate=pcm_sample_rate,
        pcm_channels=pcm_channels,
        pcm_sample_width=pcm_sample_width,
    )
    foreground_pcm = clip_pcm(
        foreground_pcm,
        start_seconds=foreground_clip_start_seconds,
        duration_seconds=foreground_clip_duration_seconds,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
    )
    background_pcm = clip_pcm(
        background_pcm,
        start_seconds=background_clip_start_seconds,
        duration_seconds=background_clip_duration_seconds,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
    )
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
        pipeline=pipeline,
        gain=1.0,
        simulate_stop_flush=simulate_stop_flush,
    )
    result.label = (
        f"{foreground_path.name} @ gain={format_gain(foreground_gain)}"
        f"{describe_clip(foreground_clip_start_seconds, foreground_clip_duration_seconds)} "
        f"+ bg({background_path.name} @ {format_gain(background_gain)}"
        f"{describe_clip(background_clip_start_seconds, background_clip_duration_seconds)}, "
        f"offset={background_offset_seconds:.2f}s, tail={tail_silence_seconds:.2f}s)"
    )
    result.path = foreground_path
    result.scenario = {
        "mode": "mixed",
        "pipeline": pipeline,
        "foreground_path": str(foreground_path),
        "foreground_input_format": foreground_format,
        "foreground_gain": foreground_gain,
        "foreground_clip_start_seconds": foreground_clip_start_seconds,
        "foreground_clip_duration_seconds": foreground_clip_duration_seconds,
        "background_path": str(background_path),
        "background_input_format": background_format,
        "background_gain": background_gain,
        "background_clip_start_seconds": background_clip_start_seconds,
        "background_clip_duration_seconds": background_clip_duration_seconds,
        "background_offset_seconds": background_offset_seconds,
        "tail_silence_seconds": tail_silence_seconds,
        "simulate_stop_flush": simulate_stop_flush,
    }
    return result


def format_counter(counter: Counter) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}:{value}" for key, value in counter.most_common())


def timeline_event_to_dict(event: TimelineEvent) -> dict[str, Any]:
    return {
        "source": event.source,
        "action": event.action,
        "reason": event.reason,
        "packet_index": event.packet_index,
        "stream_start_seconds": event.stream_start_seconds,
        "stream_end_seconds": event.stream_end_seconds,
        "buffer_duration_seconds": event.buffer_duration_seconds,
        "trailing_silence_detected": event.trailing_silence_detected,
        "speech_gate_reason": event.speech_gate_reason,
        "tail_gate_reason": event.tail_gate_reason,
        "rms": event.rms,
        "peak": event.peak,
        "active_ratio": event.active_ratio,
        "voiced_ratio": event.voiced_ratio,
        "silence_ratio": event.silence_ratio,
        "active_seconds": event.active_seconds,
        "voiced_seconds": event.voiced_seconds,
        "max_active_run_seconds": event.max_active_run_seconds,
        "max_voiced_run_seconds": event.max_voiced_run_seconds,
        "voiced_density": event.voiced_density,
    }


def audio_analysis_result_to_dict(result: AudioAnalysisResult) -> dict[str, Any]:
    return {
        "label": result.label,
        "path": str(result.path),
        "gain": result.gain,
        "scenario": result.scenario,
        "duration_seconds": result.duration_seconds,
        "process_count": result.process_count,
        "drop_count": result.drop_count,
        "waiting_count": result.waiting_count,
        "process_reasons": dict(result.process_reasons),
        "drop_reasons": dict(result.drop_reasons),
        "speech_gate_reasons": dict(result.gate_reasons),
        "tail_gate_reasons": dict(result.tail_gate_reasons),
        "final_buffer_seconds": result.final_buffer_seconds,
        "stop_flush_event": (
            timeline_event_to_dict(result.stop_flush_event)
            if result.stop_flush_event
            else None
        ),
        "timeline_events": [timeline_event_to_dict(event) for event in result.timeline_events],
    }


def write_json_results(results: list[AudioAnalysisResult], output_path: Path) -> None:
    payload = [audio_analysis_result_to_dict(result) for result in results]
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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
        f"active_run={event.max_active_run_seconds:.2f}s "
        f"voiced_run={event.max_voiced_run_seconds:.2f}s "
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
    parser = argparse.ArgumentParser(description="Offline replay wav/pcm files and inspect realtime chunk policy behavior.")
    parser.add_argument("paths", nargs="+", help="Audio file paths to analyze")
    parser.add_argument(
        "--pipeline",
        choices=("legacy", "simplified"),
        default="simplified",
        help="Realtime gating pipeline to replay (default: simplified, matching current online development path)",
    )
    parser.add_argument(
        "--input-format",
        choices=("auto", "wav", "pcm"),
        default="auto",
        help="Input format for primary/background audio (default: auto by suffix)",
    )
    parser.add_argument(
        "--pcm-sample-rate",
        type=int,
        default=16000,
        help="Sample rate used when reading raw PCM files (default: 16000)",
    )
    parser.add_argument(
        "--pcm-channels",
        type=int,
        default=1,
        help="Channel count used when reading raw PCM files (default: 1)",
    )
    parser.add_argument(
        "--pcm-sample-width",
        type=int,
        default=2,
        help="Bytes per sample used when reading raw PCM files (default: 2 for int16)",
    )
    parser.add_argument("--packet-samples", type=int, default=512, help="Simulated frontend packet size in samples (default: 512)")
    parser.add_argument(
        "--gains",
        nargs="+",
        type=float,
        default=[1.0],
        help="Optional gain multipliers to replay, e.g. --gains 1.0 0.5 0.25",
    )
    parser.add_argument("--clip-start-seconds", type=float, default=0.0, help="Clip primary wav from this start offset before analysis")
    parser.add_argument("--clip-duration-seconds", type=float, help="Optional clip duration for the primary wav")
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
        "--mix-background-start-seconds",
        type=float,
        default=0.0,
        help="Clip background wav from this start offset before mixing",
    )
    parser.add_argument(
        "--mix-background-duration-seconds",
        type=float,
        help="Optional clip duration for the background wav before mixing",
    )
    parser.add_argument(
        "--mix-background-offset-seconds",
        nargs="+",
        type=float,
        default=[0.0],
        help="One or more offsets in seconds before the background wav starts inside the mixed scene",
    )
    parser.add_argument(
        "--mix-tail-silence-seconds",
        type=float,
        default=0.0,
        help="Optional silence appended after the mixed scene to make stop-flush / tail behavior easier to inspect",
    )
    parser.add_argument(
        "--json-output",
        help="Optional JSON output path for structured analysis results",
    )
    args = parser.parse_args()

    policy = build_realtime_chunk_policy(simplified=args.pipeline == "simplified")
    background_path = Path(args.mix_background).expanduser().resolve() if args.mix_background else None
    all_results: list[AudioAnalysisResult] = []
    for raw_path in args.paths:
        path = Path(raw_path).expanduser().resolve()
        if background_path:
            analysis_inputs = [
                analyze_mixed_files(
                    path,
                    background_path,
                    policy,
                    packet_samples=args.packet_samples,
                    input_format=args.input_format,
                    pcm_sample_rate=args.pcm_sample_rate,
                    pcm_channels=args.pcm_channels,
                    pcm_sample_width=args.pcm_sample_width,
                    pipeline=args.pipeline,
                    foreground_gain=gain,
                    background_gain=background_gain,
                    foreground_clip_start_seconds=args.clip_start_seconds,
                    foreground_clip_duration_seconds=args.clip_duration_seconds,
                    background_clip_start_seconds=args.mix_background_start_seconds,
                    background_clip_duration_seconds=args.mix_background_duration_seconds,
                    background_offset_seconds=background_offset_seconds,
                    tail_silence_seconds=args.mix_tail_silence_seconds,
                    simulate_stop_flush=not args.no_stop_flush,
                )
                for gain in args.gains
                for background_gain in args.mix_background_gains
                for background_offset_seconds in args.mix_background_offset_seconds
            ]
        else:
            analysis_inputs = [
                analyze_file(
                    path,
                    policy,
                    packet_samples=args.packet_samples,
                    input_format=args.input_format,
                    pcm_sample_rate=args.pcm_sample_rate,
                    pcm_channels=args.pcm_channels,
                    pcm_sample_width=args.pcm_sample_width,
                    pipeline=args.pipeline,
                    gain=gain,
                    clip_start_seconds=args.clip_start_seconds,
                    clip_duration_seconds=args.clip_duration_seconds,
                    simulate_stop_flush=not args.no_stop_flush,
                )
                for gain in args.gains
            ]

        for result in analysis_inputs:
            all_results.append(result)
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

    if args.json_output:
        output_path = Path(args.json_output).expanduser().resolve()
        write_json_results(all_results, output_path)
        print(f"json_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
