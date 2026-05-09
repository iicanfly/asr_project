from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Sequence


DEFAULT_FILLER_WORDS = ("嗯", "啊", "呃", "那", "哦", "唔", "嘿", "咳")


@dataclass(frozen=True)
class RealtimeChunkPolicy:
    min_audio_seconds: float = 1.0
    max_audio_seconds: float = 30.0
    chunk_seconds: float = 10.0
    min_speech_frames: int = 100
    tail_silence_bytes: int = 4000
    sample_rate: int = 16000
    bytes_per_sample: int = 2
    frame_size: int = 256
    silence_threshold: float = 0.001
    peak_threshold: int = 100
    silence_ratio_threshold: float = 0.8


@dataclass(frozen=True)
class ChunkDecision:
    should_process: bool
    reason: str
    audio_duration_seconds: float
    trailing_silence_detected: bool


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


def decide_chunk_processing(audio_data: bytes, policy: RealtimeChunkPolicy) -> ChunkDecision:
    duration_seconds = pcm_bytes_to_duration_seconds(
        audio_data,
        sample_rate=policy.sample_rate,
        bytes_per_sample=policy.bytes_per_sample,
    )

    if duration_seconds >= policy.max_audio_seconds:
        return ChunkDecision(
            should_process=True,
            reason="max_duration_reached",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
        )

    if duration_seconds >= policy.chunk_seconds:
        return ChunkDecision(
            should_process=True,
            reason="chunk_duration_reached",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
        )

    if duration_seconds < policy.min_audio_seconds:
        return ChunkDecision(
            should_process=False,
            reason="below_min_duration",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
        )

    min_required_bytes = policy.min_speech_frames * 4
    if len(audio_data) < min_required_bytes:
        return ChunkDecision(
            should_process=False,
            reason="insufficient_frames",
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
        )

    tail_audio = audio_data[-policy.tail_silence_bytes :]
    trailing_silence_detected = detect_silence(
        tail_audio,
        frame_size=policy.frame_size,
        silence_threshold=policy.silence_threshold,
        peak_threshold=policy.peak_threshold,
        silence_ratio_threshold=policy.silence_ratio_threshold,
    )

    return ChunkDecision(
        should_process=trailing_silence_detected,
        reason="tail_silence_detected" if trailing_silence_detected else "waiting_for_more_audio",
        audio_duration_seconds=duration_seconds,
        trailing_silence_detected=trailing_silence_detected,
    )


def should_filter_asr_result(text: str, filler_words: Sequence[str] = DEFAULT_FILLER_WORDS) -> bool:
    if not text or not text.strip():
        return True

    normalized_text = text.strip()
    filler_count = sum(normalized_text.count(word) for word in filler_words)

    if len(normalized_text) > 0 and filler_count / len(normalized_text) > 0.5:
        return True
    if len(normalized_text) >= 3 and len(set(normalized_text)) <= 2:
        return True
    if len(normalized_text) < 2:
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
