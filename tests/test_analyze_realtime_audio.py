import importlib.util
import sys
import unittest
from pathlib import Path

from services.asr_service import RealtimeChunkPolicy


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "analyze_realtime_audio.py"
SPEC = importlib.util.spec_from_file_location("analyze_realtime_audio", MODULE_PATH)
analyze_realtime_audio = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = analyze_realtime_audio
assert SPEC.loader is not None
SPEC.loader.exec_module(analyze_realtime_audio)


def pcm_window(value: int, sample_count: int) -> bytes:
    return b"".join(value.to_bytes(2, "little", signed=True) for _ in range(sample_count))


class RealtimeAudioAnalyzerTests(unittest.TestCase):
    def test_analyze_pcm_records_chunk_process_event(self):
        policy = RealtimeChunkPolicy(chunk_seconds=1.0, max_audio_seconds=5.0)
        strong_audio = pcm_window(900, 16000)

        result = analyze_realtime_audio.analyze_pcm(
            strong_audio,
            policy,
            packet_samples=512,
            simulate_stop_flush=False,
        )

        self.assertEqual(result.process_count, 1)
        self.assertEqual(result.drop_count, 0)
        self.assertIsNone(result.stop_flush_event)

        significant_events = [event for event in result.timeline_events if event.action != "waiting"]
        self.assertEqual(len(significant_events), 1)
        self.assertEqual(significant_events[0].action, "process")
        self.assertEqual(significant_events[0].reason, "chunk_duration_reached")
        self.assertEqual(significant_events[0].speech_gate_reason, "strong_signal")
        self.assertAlmostEqual(significant_events[0].stream_end_seconds, 1.0, places=2)

    def test_analyze_pcm_simulates_strong_stop_flush(self):
        policy = RealtimeChunkPolicy(chunk_seconds=10.0, stop_flush_min_seconds=0.35)
        tail_audio = pcm_window(900, int(16000 * 0.45))

        result = analyze_realtime_audio.analyze_pcm(
            tail_audio,
            policy,
            packet_samples=512,
            simulate_stop_flush=True,
        )

        self.assertEqual(result.process_count, 0)
        self.assertIsNotNone(result.stop_flush_event)
        self.assertEqual(result.stop_flush_event.action, "stop_process")
        self.assertEqual(result.stop_flush_event.reason, "stop_flush_pending_audio")
        self.assertEqual(result.stop_flush_event.speech_gate_reason, "strong_signal")

    def test_analyze_pcm_simulates_weak_stop_flush_drop(self):
        policy = RealtimeChunkPolicy(chunk_seconds=10.0, stop_flush_min_seconds=0.35)
        weak_audio = pcm_window(80, int(16000 * 0.45))

        result = analyze_realtime_audio.analyze_pcm(
            weak_audio,
            policy,
            packet_samples=512,
            simulate_stop_flush=True,
        )

        self.assertEqual(result.process_count, 0)
        self.assertIsNotNone(result.stop_flush_event)
        self.assertEqual(result.stop_flush_event.action, "stop_drop")
        self.assertEqual(result.stop_flush_event.reason, "stop_flush_drop_weak_audio")
        self.assertEqual(result.stop_flush_event.speech_gate_reason, "no_usable_speech")


if __name__ == "__main__":
    unittest.main()
