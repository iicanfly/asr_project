from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from dataclasses import replace
from typing import Mapping
from typing import Sequence


DEFAULT_FILLER_WORDS = ("嗯", "啊", "呃", "额", "哦", "唔", "嘿", "咳", "呀", "哎", "诶", "欸", "哈", "嘘")
DEFAULT_ALLOWED_SHORT_PHRASES = ("好的", "可以", "收到", "是的", "行的", "没事", "对的")
DEFAULT_LOW_INFORMATION_SEGMENTS = (
    "嗯",
    "啊",
    "呃",
    "额",
    "哦",
    "唔",
    "嘿",
    "咳",
    "呀",
    "哎",
    "诶",
    "欸",
    "哈",
    "你好",
    "您好",
    "谢谢",
    "多谢",
    "嘘",
    "yes",
    "yeah",
    "yep",
    "ok",
    "okay",
    "hello",
    "hi",
    "huh",
    "uh",
    "uhh",
    "thanks",
    "thank you",
    "thankyou",
    "what's that",
    "whats that",
    "what",
    "just",
    "right",
    "alright",
    "well",
    "was one",
    "one",
)
DEFAULT_CONTEXTUAL_LOW_INFORMATION_SEGMENTS = (
    "那",
    "对",
    "好的",
    "是的",
    "是的吧",
    "好",
    "那啥",
    "那个",
    "ok",
    "okay",
    "你好",
)
BOUNDARY_PUNCTUATION = "，。！？、；：,.!?;:~… "
SEGMENT_SPLIT_PUNCTUATION = "，。！？、；：,.!?;:~…"
SENTENCE_END_PUNCTUATION = "。！？!?；;"
CONTINUATION_ENDING_CHARS = set("的地得了着呢吗嘛吧啊呀呗么和与及并且而又在将把给让向对")


@dataclass(frozen=True)
class RealtimeChunkPolicy:
    min_audio_seconds: float = 1.0
    max_audio_seconds: float = 30.0
    chunk_seconds: float = 10.0
    stop_flush_min_seconds: float = 0.35
    min_speech_frames: int = 100
    tail_silence_bytes: int = 4000
    sample_rate: int = 16000
    bytes_per_sample: int = 2
    frame_size: int = 256
    silence_threshold: float = 0.001
    peak_threshold: int = 100
    silence_ratio_threshold: float = 0.8
    speech_rms_threshold: float = 0.004
    speech_peak_threshold: int = 280
    min_active_ratio: float = 0.12
    min_voiced_ratio: float = 0.08
    min_active_seconds: float = 0.75
    min_voiced_seconds: float = 0.4
    min_voiced_run_seconds: float = 0.08
    min_active_run_seconds: float = 0.18
    active_speech_rms_threshold: float = 0.0032
    active_speech_peak_threshold: int = 220
    min_voiced_density_for_soft_speech: float = 0.2
    tail_trigger_min_active_seconds: float = 0.28
    tail_trigger_min_voiced_seconds: float = 0.12
    tail_trigger_min_voiced_run_seconds: float = 0.06
    weak_audio_rms_threshold: float = 0.0022
    weak_audio_peak_threshold: int = 180
    strong_silence_ratio_threshold: float = 0.92
    uncertain_retain_seconds: float = 1.2


@dataclass(frozen=True)
class AudioFeatures:
    duration_seconds: float
    rms: float
    peak: int
    active_ratio: float
    voiced_ratio: float
    silence_ratio: float
    frame_count: int
    max_active_run_seconds: float
    max_voiced_run_seconds: float

    @property
    def active_seconds(self) -> float:
        return self.active_ratio * self.duration_seconds

    @property
    def voiced_seconds(self) -> float:
        return self.voiced_ratio * self.duration_seconds

    @property
    def voiced_density(self) -> float:
        if self.active_ratio <= 0:
            return 0.0
        return self.voiced_ratio / self.active_ratio


@dataclass(frozen=True)
class ChunkDecision:
    should_process: bool
    reason: str
    audio_duration_seconds: float
    trailing_silence_detected: bool
    drop_buffer: bool = False
    audio_features: AudioFeatures | None = None
    speech_gate_reason: str = ""
    tail_gate_reason: str = ""
    retain_buffer_seconds: float = 0.0
    trim_trailing_silence: bool = False


@dataclass(frozen=True)
class SegmentRewritePolicy:
    min_segment_seconds: float = 6.0
    min_segment_chunks: int = 2
    min_new_chunks_for_rewrite: int = 2
    finalize_on_tail_silence_min_seconds: float = 4.0
    finalize_on_tail_silence_min_chars: int = 14
    sentence_boundary_min_chars: int = 6
    max_segment_seconds: float = 18.0


@dataclass(frozen=True)
class SegmentRewriteDecision:
    should_emit_rewrite: bool
    should_finalize_segment: bool
    reason: str


REALTIME_POLICY_PARSERS = {
    "min_audio_seconds": float,
    "max_audio_seconds": float,
    "chunk_seconds": float,
    "stop_flush_min_seconds": float,
    "min_speech_frames": int,
    "tail_silence_bytes": int,
    "sample_rate": int,
    "bytes_per_sample": int,
    "frame_size": int,
    "silence_threshold": float,
    "peak_threshold": int,
    "silence_ratio_threshold": float,
    "speech_rms_threshold": float,
    "speech_peak_threshold": int,
    "min_active_ratio": float,
    "min_voiced_ratio": float,
    "min_active_seconds": float,
    "min_voiced_seconds": float,
    "min_voiced_run_seconds": float,
    "min_active_run_seconds": float,
    "active_speech_rms_threshold": float,
    "active_speech_peak_threshold": int,
    "min_voiced_density_for_soft_speech": float,
    "tail_trigger_min_active_seconds": float,
    "tail_trigger_min_voiced_seconds": float,
    "tail_trigger_min_voiced_run_seconds": float,
    "weak_audio_rms_threshold": float,
    "weak_audio_peak_threshold": int,
    "strong_silence_ratio_threshold": float,
    "uncertain_retain_seconds": float,
}


def load_realtime_chunk_policy_overrides(
    base_policy: RealtimeChunkPolicy,
    env: Mapping[str, str],
    *,
    mode_prefix: str | None = None,
) -> tuple[RealtimeChunkPolicy, dict[str, float | int]]:
    updates: dict[str, float | int] = {}
    normalized_prefix = (mode_prefix or "").strip().upper()

    for field_name, parser in REALTIME_POLICY_PARSERS.items():
        env_suffix = field_name.upper()
        candidate_keys = []
        if normalized_prefix:
            candidate_keys.append(f"{normalized_prefix}_REALTIME_{env_suffix}")
        candidate_keys.append(f"REALTIME_{env_suffix}")

        raw_value = None
        for key in candidate_keys:
            if key in env and str(env[key]).strip():
                raw_value = str(env[key]).strip()
                break

        if raw_value is None:
            continue

        updates[field_name] = parser(raw_value)

    if not updates:
        return base_policy, {}
    return replace(base_policy, **updates), updates


def add_wav_header(
    pcm_data: bytes,
    sample_rate: int = 16000,
    num_channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm_data)
    file_size = 36 + data_size

    header = bytearray()
    header += b"RIFF"
    header += file_size.to_bytes(4, "little")
    header += b"WAVE"
    header += b"fmt "
    header += (16).to_bytes(4, "little")
    header += (1).to_bytes(2, "little")
    header += num_channels.to_bytes(2, "little")
    header += sample_rate.to_bytes(4, "little")
    header += byte_rate.to_bytes(4, "little")
    header += block_align.to_bytes(2, "little")
    header += bits_per_sample.to_bytes(2, "little")
    header += b"data"
    header += data_size.to_bytes(4, "little")
    return bytes(header) + pcm_data


def pcm_bytes_to_duration_seconds(
    audio_data: bytes,
    sample_rate: int = 16000,
    bytes_per_sample: int = 2,
) -> float:
    if not audio_data:
        return 0.0
    return len(audio_data) / float(sample_rate * bytes_per_sample)


def detect_silence(
    audio_data: bytes,
    *,
    frame_size: int = 256,
    silence_threshold: float = 0.001,
    peak_threshold: int = 100,
    silence_ratio_threshold: float = 0.8,
) -> bool:
    """Return True when the sampled audio window is mostly silence."""
    if len(audio_data) < frame_size:
        return False

    samples = [
        int.from_bytes(audio_data[i : i + 2], "little", signed=True)
        for i in range(0, len(audio_data), 2)
    ]

    num_frames = len(samples) // frame_size
    silence_frames = 0

    for i in range(num_frames):
        start = i * frame_size
        end = start + frame_size
        frame = samples[start:end]
        if not frame:
            continue

        rms = (sum(sample ** 2 for sample in frame) / len(frame)) ** 0.5
        max_val = max(abs(sample) for sample in frame)
        normalized_rms = rms / 32768.0

        if normalized_rms < silence_threshold or max_val < peak_threshold:
            silence_frames += 1

    silence_ratio = silence_frames / max(num_frames, 1)
    return silence_ratio > silence_ratio_threshold


def extract_audio_features(
    audio_data: bytes,
    *,
    sample_rate: int = 16000,
    bytes_per_sample: int = 2,
    frame_size: int = 256,
    silence_threshold: float = 0.001,
    peak_threshold: int = 100,
    speech_rms_threshold: float = 0.004,
    speech_peak_threshold: int = 280,
) -> AudioFeatures:
    duration_seconds = pcm_bytes_to_duration_seconds(
        audio_data,
        sample_rate=sample_rate,
        bytes_per_sample=bytes_per_sample,
    )
    if not audio_data:
        return AudioFeatures(duration_seconds, 0.0, 0, 0.0, 0.0, 1.0, 0, 0.0, 0.0)

    samples = [
        int.from_bytes(audio_data[i : i + 2], "little", signed=True)
        for i in range(0, len(audio_data), 2)
    ]
    if not samples:
        return AudioFeatures(duration_seconds, 0.0, 0, 0.0, 0.0, 1.0, 0, 0.0, 0.0)

    overall_rms = (sum(sample ** 2 for sample in samples) / len(samples)) ** 0.5 / 32768.0
    overall_peak = max(abs(sample) for sample in samples)
    frame_count = len(samples) // frame_size

    if frame_count <= 0:
        return AudioFeatures(duration_seconds, overall_rms, overall_peak, 0.0, 0.0, 1.0, 0, 0.0, 0.0)

    active_frames = 0
    voiced_frames = 0
    silence_frames = 0
    current_active_run = 0
    current_voiced_run = 0
    max_active_run = 0
    max_voiced_run = 0

    for i in range(frame_count):
        start = i * frame_size
        end = start + frame_size
        frame = samples[start:end]
        if not frame:
            continue

        frame_rms = (sum(sample ** 2 for sample in frame) / len(frame)) ** 0.5 / 32768.0
        frame_peak = max(abs(sample) for sample in frame)
        is_active = frame_rms >= silence_threshold and frame_peak >= peak_threshold
        is_voiced = frame_rms >= speech_rms_threshold and frame_peak >= speech_peak_threshold

        if is_active:
            active_frames += 1
            current_active_run += 1
            max_active_run = max(max_active_run, current_active_run)
        else:
            silence_frames += 1
            current_active_run = 0

        if is_voiced:
            voiced_frames += 1
            current_voiced_run += 1
            max_voiced_run = max(max_voiced_run, current_voiced_run)
        else:
            current_voiced_run = 0

    return AudioFeatures(
        duration_seconds=duration_seconds,
        rms=overall_rms,
        peak=overall_peak,
        active_ratio=active_frames / frame_count,
        voiced_ratio=voiced_frames / frame_count,
        silence_ratio=silence_frames / frame_count,
        frame_count=frame_count,
        max_active_run_seconds=max_active_run * frame_size / sample_rate,
        max_voiced_run_seconds=max_voiced_run * frame_size / sample_rate,
    )


def _adaptive_presence_seconds(
    duration_seconds: float,
    *,
    cap_seconds: float,
    ratio_floor: float,
    minimum_floor: float,
) -> float:
    return min(cap_seconds, max(minimum_floor, duration_seconds * ratio_floor))


def describe_usable_speech(features: AudioFeatures, policy: RealtimeChunkPolicy) -> str:
    if features.duration_seconds <= 0:
        return "empty_audio"

    strong_signal = features.rms >= policy.speech_rms_threshold and features.peak >= policy.speech_peak_threshold
    required_voiced_seconds = _adaptive_presence_seconds(
        features.duration_seconds,
        cap_seconds=policy.min_voiced_seconds,
        ratio_floor=0.08,
        minimum_floor=0.12,
    )
    required_active_seconds = _adaptive_presence_seconds(
        features.duration_seconds,
        cap_seconds=policy.min_active_seconds,
        ratio_floor=0.18,
        minimum_floor=0.24,
    )
    sustained_voiced = (
        features.voiced_ratio >= policy.min_voiced_ratio
        and features.voiced_seconds >= required_voiced_seconds
        and features.max_voiced_run_seconds >= policy.min_voiced_run_seconds
    )
    if strong_signal:
        return "strong_signal"
    if sustained_voiced:
        return "sustained_voiced"

    fragmented_voiced_presence = (
        features.voiced_ratio >= policy.min_voiced_ratio
        and features.voiced_seconds >= required_voiced_seconds
        and features.max_voiced_run_seconds < policy.min_voiced_run_seconds
    )
    if fragmented_voiced_presence:
        return "fragmented_voiced_presence"

    sustained_active_speech = (
        features.active_ratio >= policy.min_active_ratio
        and features.active_seconds >= required_active_seconds
        and features.max_active_run_seconds >= policy.min_active_run_seconds
        and features.rms >= policy.active_speech_rms_threshold
        and features.peak >= policy.active_speech_peak_threshold
        and features.voiced_ratio >= (policy.min_voiced_ratio * 0.5)
        and features.max_voiced_run_seconds >= (policy.min_voiced_run_seconds * 0.5)
        and features.voiced_density >= policy.min_voiced_density_for_soft_speech
    )
    if sustained_active_speech:
        return "sustained_soft_speech"
    return "no_usable_speech"


def has_usable_speech(features: AudioFeatures, policy: RealtimeChunkPolicy) -> bool:
    return describe_usable_speech(features, policy) in {
        "strong_signal",
        "sustained_voiced",
        "sustained_soft_speech",
    }


def describe_tail_triggerable_speech(features: AudioFeatures, policy: RealtimeChunkPolicy) -> str:
    usable_reason = describe_usable_speech(features, policy)
    if usable_reason in {"empty_audio", "no_usable_speech", "fragmented_voiced_presence"}:
        return usable_reason

    strong_signal = features.rms >= policy.speech_rms_threshold and features.peak >= policy.speech_peak_threshold
    if strong_signal:
        return "tail_strong_signal"

    if (
        features.active_seconds >= policy.tail_trigger_min_active_seconds
        and features.voiced_seconds >= policy.tail_trigger_min_voiced_seconds
        and features.max_voiced_run_seconds >= policy.tail_trigger_min_voiced_run_seconds
    ):
        return "tail_sustained_presence"
    if (
        features.active_seconds >= policy.tail_trigger_min_active_seconds
        and features.voiced_seconds >= policy.tail_trigger_min_voiced_seconds
        and features.max_voiced_run_seconds < policy.tail_trigger_min_voiced_run_seconds
    ):
        return "tail_fragmented_presence"
    return "tail_presence_too_brief"


def has_tail_triggerable_speech(features: AudioFeatures, policy: RealtimeChunkPolicy) -> bool:
    return describe_tail_triggerable_speech(features, policy) in {"tail_strong_signal", "tail_sustained_presence"}


def is_weak_background_audio(features: AudioFeatures, policy: RealtimeChunkPolicy) -> bool:
    return (
        features.silence_ratio >= policy.strong_silence_ratio_threshold
        or (
            features.rms < policy.weak_audio_rms_threshold
            and features.peak < policy.weak_audio_peak_threshold
            and features.voiced_ratio < policy.min_voiced_ratio
        )
    )


def has_potential_short_speech(features: AudioFeatures, policy: RealtimeChunkPolicy) -> bool:
    min_short_voiced_run = max(0.045, policy.tail_trigger_min_voiced_run_seconds * 0.75)
    min_short_voiced_seconds = max(0.08, policy.tail_trigger_min_voiced_seconds * 0.6)
    min_short_active_run = max(0.12, policy.min_active_run_seconds * 0.7)
    min_short_density = max(0.18, policy.min_voiced_density_for_soft_speech * 0.75)

    if features.max_voiced_run_seconds >= min_short_voiced_run:
        return True

    return (
        features.max_active_run_seconds >= min_short_active_run
        and features.voiced_seconds >= min_short_voiced_seconds
        and features.voiced_density >= min_short_density
    )


def retain_realtime_buffer(audio_data: bytes, decision: ChunkDecision, policy: RealtimeChunkPolicy) -> bytes:
    if decision.drop_buffer or not audio_data:
        return b""

    retained_audio = audio_data
    if decision.trim_trailing_silence and len(retained_audio) > policy.tail_silence_bytes:
        retained_audio = retained_audio[:-policy.tail_silence_bytes]

    retain_seconds = max(0.0, decision.retain_buffer_seconds)
    if retain_seconds <= 0:
        return retained_audio

    retain_bytes = int(retain_seconds * policy.sample_rate * policy.bytes_per_sample)
    if retain_bytes <= 0 or len(retained_audio) <= retain_bytes:
        return retained_audio
    return retained_audio[-retain_bytes:]


def _build_trigger_wait_decision(
    *,
    reason: str,
    duration_seconds: float,
    features: AudioFeatures,
    speech_gate_reason: str,
    tail_gate_reason: str = "",
) -> ChunkDecision:
    return ChunkDecision(
        should_process=False,
        reason=reason,
        audio_duration_seconds=duration_seconds,
        trailing_silence_detected=False,
        audio_features=features,
        speech_gate_reason=speech_gate_reason,
        tail_gate_reason=tail_gate_reason,
    )


def _decide_simplified_upload_gate(
    *,
    trigger_reason: str,
    duration_seconds: float,
    trailing_silence_detected: bool,
    features: AudioFeatures,
    speech_gate_reason: str,
    tail_gate_reason: str,
    policy: RealtimeChunkPolicy,
) -> ChunkDecision:
    if has_usable_speech(features, policy):
        return ChunkDecision(
            should_process=True,
            reason=trigger_reason,
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=trailing_silence_detected,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
            tail_gate_reason=tail_gate_reason,
        )

    if trailing_silence_detected and has_potential_short_speech(features, policy):
        return ChunkDecision(
            should_process=True,
            reason="tail_short_speech_detected",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=True,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
            tail_gate_reason=tail_gate_reason,
        )

    if is_weak_background_audio(features, policy):
        return ChunkDecision(
            should_process=False,
            reason=f"simplified_drop_weak_audio_after_{trigger_reason}",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=trailing_silence_detected,
            drop_buffer=True,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
            tail_gate_reason=tail_gate_reason,
        )

    return ChunkDecision(
        should_process=True,
        reason=f"simplified_fallback_{trigger_reason}",
        audio_duration_seconds=duration_seconds,
        trailing_silence_detected=trailing_silence_detected,
        audio_features=features,
        speech_gate_reason=speech_gate_reason,
        tail_gate_reason=tail_gate_reason,
    )


def decide_chunk_processing_simple(audio_data: bytes, policy: RealtimeChunkPolicy) -> ChunkDecision:
    features = extract_audio_features(
        audio_data,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
        frame_size=policy.frame_size,
        silence_threshold=policy.silence_threshold,
        peak_threshold=policy.peak_threshold,
        speech_rms_threshold=policy.speech_rms_threshold,
        speech_peak_threshold=policy.speech_peak_threshold,
    )
    duration_seconds = features.duration_seconds
    speech_gate_reason = describe_usable_speech(features, policy)

    if duration_seconds < policy.min_audio_seconds:
        return _build_trigger_wait_decision(
            reason="below_min_duration",
            duration_seconds=duration_seconds,
            features=features,
            speech_gate_reason=speech_gate_reason,
        )

    min_required_bytes = policy.min_speech_frames * 4
    if len(audio_data) < min_required_bytes:
        return _build_trigger_wait_decision(
            reason="insufficient_frames",
            duration_seconds=duration_seconds,
            features=features,
            speech_gate_reason=speech_gate_reason,
        )

    trigger_reason = ""
    trailing_silence_detected = False
    tail_gate_reason = ""

    if duration_seconds >= policy.max_audio_seconds:
        trigger_reason = "max_duration_reached"
    elif duration_seconds >= policy.chunk_seconds:
        trigger_reason = "chunk_duration_reached"
    else:
        tail_audio = audio_data[-policy.tail_silence_bytes :]
        trailing_silence_detected = detect_silence(
            tail_audio,
            frame_size=policy.frame_size,
            silence_threshold=policy.silence_threshold,
            peak_threshold=policy.peak_threshold,
            silence_ratio_threshold=policy.silence_ratio_threshold,
        )
        if not trailing_silence_detected:
            return _build_trigger_wait_decision(
                reason="waiting_for_more_audio",
                duration_seconds=duration_seconds,
                features=features,
                speech_gate_reason=speech_gate_reason,
            )
        trigger_reason = "tail_silence_detected"
        tail_gate_reason = describe_tail_triggerable_speech(features, policy)

    return _decide_simplified_upload_gate(
        trigger_reason=trigger_reason,
        duration_seconds=duration_seconds,
        trailing_silence_detected=trailing_silence_detected,
        features=features,
        speech_gate_reason=speech_gate_reason,
        tail_gate_reason=tail_gate_reason,
        policy=policy,
    )


def decide_stop_flush_simple(audio_data: bytes, policy: RealtimeChunkPolicy) -> ChunkDecision:
    features = extract_audio_features(
        audio_data,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
        frame_size=policy.frame_size,
        silence_threshold=policy.silence_threshold,
        peak_threshold=policy.peak_threshold,
        speech_rms_threshold=policy.speech_rms_threshold,
        speech_peak_threshold=policy.speech_peak_threshold,
    )
    duration_seconds = features.duration_seconds
    speech_gate_reason = describe_usable_speech(features, policy)

    if duration_seconds <= 0:
        return ChunkDecision(
            should_process=False,
            reason="stop_flush_empty_buffer",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    if duration_seconds < policy.stop_flush_min_seconds:
        return ChunkDecision(
            should_process=False,
            reason="stop_flush_below_min_duration",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    if has_usable_speech(features, policy):
        return ChunkDecision(
            should_process=True,
            reason="stop_flush_pending_audio",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    if has_potential_short_speech(features, policy):
        return ChunkDecision(
            should_process=True,
            reason="stop_flush_short_voiced_tail",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    return ChunkDecision(
        should_process=False,
        reason="stop_flush_drop_weak_audio",
        audio_duration_seconds=duration_seconds,
        trailing_silence_detected=False,
        drop_buffer=True,
        audio_features=features,
        speech_gate_reason=speech_gate_reason,
    )


def decide_chunk_processing(audio_data: bytes, policy: RealtimeChunkPolicy) -> ChunkDecision:
    features = extract_audio_features(
        audio_data,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
        frame_size=policy.frame_size,
        silence_threshold=policy.silence_threshold,
        peak_threshold=policy.peak_threshold,
        speech_rms_threshold=policy.speech_rms_threshold,
        speech_peak_threshold=policy.speech_peak_threshold,
    )
    duration_seconds = features.duration_seconds
    speech_gate_reason = describe_usable_speech(features, policy)
    potential_short_speech = has_potential_short_speech(features, policy)

    if duration_seconds >= policy.max_audio_seconds:
        if speech_gate_reason not in {"strong_signal", "sustained_voiced", "sustained_soft_speech"}:
            if potential_short_speech:
                return ChunkDecision(
                    should_process=False,
                    reason="retain_uncertain_audio_at_max_duration",
                    audio_duration_seconds=duration_seconds,
                    trailing_silence_detected=False,
                    audio_features=features,
                    speech_gate_reason=speech_gate_reason,
                    retain_buffer_seconds=policy.uncertain_retain_seconds,
                )
            return ChunkDecision(
                should_process=False,
                reason="drop_weak_audio_at_max_duration",
                audio_duration_seconds=duration_seconds,
                trailing_silence_detected=False,
                drop_buffer=True,
                audio_features=features,
                speech_gate_reason=speech_gate_reason,
            )
        return ChunkDecision(
            should_process=True,
            reason="max_duration_reached",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    if duration_seconds >= policy.chunk_seconds:
        if speech_gate_reason not in {"strong_signal", "sustained_voiced", "sustained_soft_speech"}:
            if potential_short_speech:
                return ChunkDecision(
                    should_process=False,
                    reason="retain_uncertain_audio_at_chunk_duration",
                    audio_duration_seconds=duration_seconds,
                    trailing_silence_detected=False,
                    audio_features=features,
                    speech_gate_reason=speech_gate_reason,
                    retain_buffer_seconds=policy.uncertain_retain_seconds,
                )
            return ChunkDecision(
                should_process=False,
                reason="drop_weak_audio_at_chunk_duration",
                audio_duration_seconds=duration_seconds,
                trailing_silence_detected=False,
                drop_buffer=True,
                audio_features=features,
                speech_gate_reason=speech_gate_reason,
            )
        return ChunkDecision(
            should_process=True,
            reason="chunk_duration_reached",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    if duration_seconds < policy.min_audio_seconds:
        return ChunkDecision(
            should_process=False,
            reason="below_min_duration",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    min_required_bytes = policy.min_speech_frames * 4
    if len(audio_data) < min_required_bytes:
        return ChunkDecision(
            should_process=False,
            reason="insufficient_frames",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    tail_audio = audio_data[-policy.tail_silence_bytes :]
    trailing_silence_detected = detect_silence(
        tail_audio,
        frame_size=policy.frame_size,
        silence_threshold=policy.silence_threshold,
        peak_threshold=policy.peak_threshold,
        silence_ratio_threshold=policy.silence_ratio_threshold,
    )
    usable_speech = speech_gate_reason in {"strong_signal", "sustained_voiced", "sustained_soft_speech"}
    tail_gate_reason = describe_tail_triggerable_speech(features, policy)
    tail_triggerable_speech = tail_gate_reason in {"tail_strong_signal", "tail_sustained_presence"}
    weak_background = is_weak_background_audio(features, policy)

    if trailing_silence_detected and weak_background and not usable_speech:
        if potential_short_speech:
            return ChunkDecision(
                should_process=False,
                reason="retain_brief_tail_speech",
                audio_duration_seconds=duration_seconds,
                trailing_silence_detected=True,
                audio_features=features,
                speech_gate_reason=speech_gate_reason,
                tail_gate_reason=tail_gate_reason,
                retain_buffer_seconds=policy.uncertain_retain_seconds,
                trim_trailing_silence=True,
            )
        return ChunkDecision(
            should_process=False,
            reason="drop_weak_background_after_tail_silence",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=True,
            drop_buffer=True,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
            tail_gate_reason=tail_gate_reason,
        )

    if trailing_silence_detected and not tail_triggerable_speech and features.active_seconds > 0:
        if potential_short_speech:
            return ChunkDecision(
                should_process=False,
                reason="retain_brief_tail_speech",
                audio_duration_seconds=duration_seconds,
                trailing_silence_detected=True,
                audio_features=features,
                speech_gate_reason=speech_gate_reason,
                tail_gate_reason=tail_gate_reason,
                retain_buffer_seconds=policy.uncertain_retain_seconds,
                trim_trailing_silence=True,
            )
        return ChunkDecision(
            should_process=False,
            reason="drop_brief_tail_speech",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=True,
            drop_buffer=True,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
            tail_gate_reason=tail_gate_reason,
        )

    return ChunkDecision(
        should_process=trailing_silence_detected and tail_triggerable_speech,
        reason=(
            "tail_silence_detected"
            if trailing_silence_detected and tail_triggerable_speech
            else "waiting_for_more_audio"
        ),
        audio_duration_seconds=duration_seconds,
        trailing_silence_detected=trailing_silence_detected,
        audio_features=features,
        speech_gate_reason=speech_gate_reason,
        tail_gate_reason=tail_gate_reason,
    )


def decide_segment_rewrite(
    *,
    segment_duration_seconds: float,
    segment_chunk_count: int,
    last_rewrite_chunk_count: int,
    latest_chunk_reason: str,
    current_segment_text: str,
    policy: SegmentRewritePolicy,
) -> SegmentRewriteDecision:
    chunk_delta = max(0, segment_chunk_count - last_rewrite_chunk_count)
    enough_for_regular_rewrite = (
        segment_chunk_count >= policy.min_segment_chunks
        and segment_duration_seconds >= policy.min_segment_seconds
        and chunk_delta >= policy.min_new_chunks_for_rewrite
    )

    refined_segment_text = refine_asr_result_text(current_segment_text)
    dense_segment_text = collapse_transcript_text(refined_segment_text)
    segment_has_sentence_boundary = looks_like_sentence_boundary(
        refined_segment_text,
        min_chars=policy.sentence_boundary_min_chars,
    )
    long_tail_silence_text = len(dense_segment_text) >= policy.finalize_on_tail_silence_min_chars

    finalize_for_silence = (
        latest_chunk_reason == "tail_silence_detected"
        and segment_duration_seconds >= policy.finalize_on_tail_silence_min_seconds
        and (segment_has_sentence_boundary or long_tail_silence_text)
    )
    finalize_for_max_duration = segment_duration_seconds >= policy.max_segment_seconds
    should_finalize_segment = finalize_for_silence or finalize_for_max_duration

    should_emit_rewrite = enough_for_regular_rewrite
    if should_finalize_segment and segment_chunk_count >= policy.min_segment_chunks and chunk_delta > 0:
        should_emit_rewrite = True

    reason_parts = []
    if enough_for_regular_rewrite:
        reason_parts.append("segment_rewrite_ready")
    if finalize_for_silence:
        reason_parts.append("segment_tail_silence_finalize")
        if segment_has_sentence_boundary:
            reason_parts.append("segment_sentence_boundary")
        elif long_tail_silence_text:
            reason_parts.append("segment_long_text_boundary")
    if finalize_for_max_duration:
        reason_parts.append("segment_max_duration_finalize")
    if not reason_parts:
        reason_parts.append("segment_accumulating")

    return SegmentRewriteDecision(
        should_emit_rewrite=should_emit_rewrite,
        should_finalize_segment=should_finalize_segment,
        reason="+".join(reason_parts),
    )


def decide_stop_flush(audio_data: bytes, policy: RealtimeChunkPolicy) -> ChunkDecision:
    features = extract_audio_features(
        audio_data,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
        frame_size=policy.frame_size,
        silence_threshold=policy.silence_threshold,
        peak_threshold=policy.peak_threshold,
        speech_rms_threshold=policy.speech_rms_threshold,
        speech_peak_threshold=policy.speech_peak_threshold,
    )
    duration_seconds = features.duration_seconds
    speech_gate_reason = describe_usable_speech(features, policy)
    potential_short_speech = has_potential_short_speech(features, policy)

    if duration_seconds <= 0:
        return ChunkDecision(
            should_process=False,
            reason="stop_flush_empty_buffer",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    if duration_seconds < policy.stop_flush_min_seconds:
        return ChunkDecision(
            should_process=False,
            reason="stop_flush_below_min_duration",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    if is_weak_background_audio(features, policy) or speech_gate_reason not in {"strong_signal", "sustained_voiced", "sustained_soft_speech"}:
        if potential_short_speech:
            return ChunkDecision(
                should_process=True,
                reason="stop_flush_short_voiced_tail",
                audio_duration_seconds=duration_seconds,
                trailing_silence_detected=False,
                audio_features=features,
                speech_gate_reason=speech_gate_reason,
            )
        return ChunkDecision(
            should_process=False,
            reason="stop_flush_drop_weak_audio",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
            drop_buffer=True,
            audio_features=features,
            speech_gate_reason=speech_gate_reason,
        )

    return ChunkDecision(
        should_process=True,
        reason="stop_flush_pending_audio",
        audio_duration_seconds=duration_seconds,
        trailing_silence_detected=False,
        audio_features=features,
        speech_gate_reason=speech_gate_reason,
    )


def _build_filler_pattern(filler_words: Sequence[str]) -> str:
    ordered = sorted({word.strip() for word in filler_words if word and word.strip()}, key=len, reverse=True)
    if not ordered:
        return ""
    return "|".join(re.escape(word) for word in ordered)


def _normalize_asr_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    normalized = normalized.replace("。 。", "。").replace("， ，", "，")
    return normalized


def _normalize_information_segment(text: str) -> str:
    normalized = _normalize_asr_text(text).casefold()
    normalized = re.sub(rf"[{re.escape(BOUNDARY_PUNCTUATION)}]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _split_transcript_segments(text: str) -> list[str]:
    normalized = _normalize_asr_text(text)
    if not normalized:
        return []
    return [part.strip() for part in re.split(rf"[{re.escape(SEGMENT_SPLIT_PUNCTUATION)}]+", normalized) if part.strip()]


def _join_transcript_segments(segments: Sequence[str]) -> str:
    joined_parts: list[str] = []
    for segment in segments:
        cleaned_segment = _normalize_asr_text(segment)
        if not cleaned_segment:
            continue
        if not joined_parts:
            joined_parts.append(cleaned_segment)
            continue

        previous_segment = joined_parts[-1]
        if _contains_cjk(previous_segment) and _contains_cjk(cleaned_segment):
            joined_parts[-1] = previous_segment + cleaned_segment
        elif previous_segment[-1].isalnum() and cleaned_segment[0].isalnum():
            joined_parts.append(f" {cleaned_segment}")
        else:
            joined_parts.append(cleaned_segment)

    return "".join(joined_parts).strip()


def _is_low_information_segment(
    text: str,
    filler_words: Sequence[str] = DEFAULT_FILLER_WORDS,
    low_information_segments: Sequence[str] = DEFAULT_LOW_INFORMATION_SEGMENTS,
    contextual_low_information_segments: Sequence[str] = (),
) -> bool:
    normalized = _normalize_information_segment(text)
    if not normalized:
        return False

    low_info_set = {_normalize_information_segment(segment) for segment in low_information_segments if segment.strip()}
    if normalized in low_info_set:
        return True

    contextual_set = {
        _normalize_information_segment(segment)
        for segment in contextual_low_information_segments
        if segment.strip()
    }
    if contextual_set and normalized in contextual_set:
        return True

    dense_text = collapse_transcript_text(normalized)
    if not dense_text:
        return True

    filler_count = sum(dense_text.count(word) for word in filler_words)
    if filler_count and filler_count >= max(1, len(dense_text) - 1):
        return True

    if len(dense_text) >= 3 and len(set(dense_text)) <= 2:
        return True

    if not _contains_cjk(normalized):
        ascii_dense = re.sub(r"[^a-z0-9]", "", normalized)
        if ascii_dense in {"ok", "okay", "yes", "yeah", "yep", "hi", "hello", "huh", "uh", "uhh", "thanks", "thankyou", "whatsthat", "wasone", "one"}:
            return True
        word_tokens = [token for token in normalized.split(" ") if token]
        if word_tokens and len(word_tokens) <= 3 and all(token in {"yes", "yeah", "yep", "ok", "okay", "hello", "hi", "huh", "uh", "uhh", "thanks", "thank", "you", "what", "whats", "that", "was", "one"} for token in word_tokens):
            return True

    return False


def _strip_low_information_segments(
    text: str,
    filler_words: Sequence[str] = DEFAULT_FILLER_WORDS,
    low_information_segments: Sequence[str] = DEFAULT_LOW_INFORMATION_SEGMENTS,
) -> tuple[str, int, int]:
    source_segments = _split_transcript_segments(text)
    contextual_segments: Sequence[str] = ()
    if len(source_segments) > 1:
        contextual_segments = DEFAULT_CONTEXTUAL_LOW_INFORMATION_SEGMENTS

    def is_tail_noise_candidate(segment_text: str) -> bool:
        normalized_segment = _normalize_asr_text(segment_text)
        if not normalized_segment:
            return True
        if normalized_segment in DEFAULT_ALLOWED_SHORT_PHRASES:
            return False
        dense_segment = collapse_transcript_text(normalized_segment)
        if not dense_segment:
            return True
        if len(dense_segment) <= 1:
            return True
        if len(dense_segment) <= 2 and not any(char.isdigit() for char in dense_segment):
            return True
        if len(dense_segment) >= 3 and len(set(dense_segment)) <= 2:
            return True
        return False

    cleaned_segments: list[str] = []
    low_information_count = 0
    meaningful_count = 0
    segment_is_low_information: list[bool] = []

    for segment in source_segments:
        is_low_information = _is_low_information_segment(
            segment,
            filler_words=filler_words,
            low_information_segments=low_information_segments,
            contextual_low_information_segments=contextual_segments,
        )
        segment_is_low_information.append(is_low_information)
        if is_low_information:
            low_information_count += 1
            continue
        cleaned_segments.append(segment)
        meaningful_count += 1

    if meaningful_count > 0 and source_segments:
        tail_start = len(source_segments)
        tail_noise_count = 0
        for index in range(len(source_segments) - 1, -1, -1):
            if segment_is_low_information[index]:
                tail_start = index
                tail_noise_count += 1
                continue
            if tail_noise_count > 0 and is_tail_noise_candidate(source_segments[index]):
                tail_start = index
                tail_noise_count += 1
                continue
            break

        if tail_noise_count >= 2 and tail_start < len(source_segments):
            cleaned_segments = []
            low_information_count = 0
            meaningful_count = 0
            for index, segment in enumerate(source_segments):
                is_low_information = segment_is_low_information[index] or index >= tail_start
                if is_low_information:
                    low_information_count += 1
                    continue
                cleaned_segments.append(segment)
                meaningful_count += 1

    return _join_transcript_segments(cleaned_segments), low_information_count, meaningful_count


def collapse_transcript_text(text: str) -> str:
    return re.sub(rf"[{re.escape(BOUNDARY_PUNCTUATION)}\s]", "", _normalize_asr_text(text))


def looks_like_sentence_boundary(text: str, *, min_chars: int = 6) -> bool:
    refined_text = _normalize_asr_text(text)
    if not refined_text:
        return False

    dense_text = collapse_transcript_text(refined_text)
    if len(dense_text) < min_chars:
        return False

    if refined_text[-1] in SENTENCE_END_PUNCTUATION:
        return True

    return dense_text[-1] not in CONTINUATION_ENDING_CHARS


def is_effective_text_update(previous_text: str, new_text: str) -> bool:
    previous_refined = refine_asr_result_text(previous_text)
    new_refined = refine_asr_result_text(new_text)

    if not new_refined:
        return False
    if not previous_refined:
        return True

    return collapse_transcript_text(previous_refined) != collapse_transcript_text(new_refined)


def refine_asr_result_text(
    text: str,
    filler_words: Sequence[str] = DEFAULT_FILLER_WORDS,
) -> str:
    normalized_text = _normalize_asr_text(text)
    if not normalized_text:
        return ""

    filler_pattern = _build_filler_pattern(filler_words)
    if not filler_pattern:
        return normalized_text

    boundary_chars = re.escape(BOUNDARY_PUNCTUATION)
    leading_pattern = re.compile(rf"^(?:(?:{filler_pattern})(?:[{boundary_chars}]*)+)+")
    trailing_pattern = re.compile(rf"(?:(?:[{boundary_chars}]*)+(?:{filler_pattern}))+[{boundary_chars}]*$")

    refined = normalized_text
    previous = None
    while refined and refined != previous:
        previous = refined
        refined = leading_pattern.sub("", refined).strip()
        refined = trailing_pattern.sub("", refined).strip()
        refined = refined.strip(BOUNDARY_PUNCTUATION).strip()

    cleaned_text, _, meaningful_count = _strip_low_information_segments(refined, filler_words=filler_words)
    if meaningful_count > 0 and cleaned_text:
        refined = cleaned_text
    return _normalize_asr_text(refined)


def should_filter_asr_result(text: str, filler_words: Sequence[str] = DEFAULT_FILLER_WORDS) -> bool:
    normalized_text = _normalize_asr_text(text)
    if not normalized_text:
        return True

    refined_text = refine_asr_result_text(normalized_text, filler_words=filler_words)
    if not refined_text:
        return True
    if refined_text in DEFAULT_ALLOWED_SHORT_PHRASES:
        return False

    cleaned_text, low_information_count, meaningful_count = _strip_low_information_segments(
        refined_text,
        filler_words=filler_words,
    )
    if meaningful_count == 0 and low_information_count > 0:
        return True
    if cleaned_text:
        refined_text = cleaned_text

    dense_text = collapse_transcript_text(refined_text)
    if not dense_text:
        return True

    filler_count = sum(dense_text.count(word) for word in filler_words)
    if len(dense_text) > 0 and filler_count / len(dense_text) >= 0.6:
        return True
    if len(dense_text) <= 4 and filler_count >= max(1, len(dense_text) - 1):
        return True

    if len(dense_text) >= 3 and len(set(dense_text)) <= 2:
        return True
    if len(dense_text) < 2:
        return True
    return False


def normalize_text_result(raw_result) -> str:
    if raw_result is None:
        return ""
    if isinstance(raw_result, str):
        return raw_result.strip()
    if isinstance(raw_result, list):
        fragments = []
        for item in raw_result:
            if isinstance(item, str):
                fragments.append(item)
                continue
            text = getattr(item, "text", None)
            if text:
                fragments.append(str(text))
                continue
            if isinstance(item, dict):
                maybe_text = item.get("text") or item.get("content")
                if maybe_text:
                    fragments.append(str(maybe_text))
        return "".join(fragments).strip()
    return str(raw_result).strip()


class ASRAdapter:
    def __init__(
        self,
        *,
        asr_mode: str,
        asr_base_url: str,
        asr_model: str,
        asr_api_key: str,
        request_timeout: float = 60.0,
    ) -> None:
        from openai import OpenAI

        self.asr_mode = asr_mode
        self.asr_base_url = asr_base_url.rstrip("/")
        self.asr_model = asr_model
        self.request_timeout = request_timeout
        self._chat_client = OpenAI(api_key=asr_api_key, base_url=asr_base_url)

    def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        *,
        filename: str = "audio.wav",
        mime_type: str = "audio/wav",
        language: str = "zh",
    ) -> str:
        if self.asr_mode == "transcriptions":
            import httpx

            response = httpx.post(
                f"{self.asr_base_url}/audio/transcriptions",
                files={"file": (filename, audio_bytes, mime_type)},
                data={"model": self.asr_model, "language": language},
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            return normalize_text_result(response.json().get("text", ""))

        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        response = self._chat_client.chat.completions.create(
            model=self.asr_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:{mime_type};base64,{base64_audio}",
                                "format": mime_type.split("/")[-1],
                            },
                        }
                    ],
                }
            ],
        )
        return normalize_text_result(response.choices[0].message.content)
