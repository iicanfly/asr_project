import unittest

from services.asr_service import (
    RealtimeChunkPolicy,
    decide_chunk_processing,
    detect_silence,
    should_filter_asr_result,
)


def pcm_window(value: int, sample_count: int) -> bytes:
    return b"".join(value.to_bytes(2, "little", signed=True) for _ in range(sample_count))


class DetectSilenceTests(unittest.TestCase):
    def test_silence_window_is_detected(self):
        silent_audio = pcm_window(0, 2048)
        self.assertTrue(detect_silence(silent_audio))

    def test_loud_window_is_not_detected_as_silence(self):
        loud_audio = pcm_window(1200, 2048)
        self.assertFalse(detect_silence(loud_audio))


class ChunkDecisionTests(unittest.TestCase):
    def test_long_audio_forces_processing(self):
        policy = RealtimeChunkPolicy(max_audio_seconds=1.0)
        audio_data = pcm_window(200, 16000 * 2)
        decision = decide_chunk_processing(audio_data, policy)
        self.assertTrue(decision.should_process)
        self.assertEqual(decision.reason, "max_duration_reached")

    def test_tail_silence_triggers_processing(self):
        policy = RealtimeChunkPolicy(
            min_audio_seconds=0.5,
            chunk_seconds=5.0,
            max_audio_seconds=30.0,
            tail_silence_bytes=4096,
        )
        speech_audio = pcm_window(600, 16000)
        tail_silence = pcm_window(0, 2048)
        decision = decide_chunk_processing(speech_audio + tail_silence, policy)
        self.assertTrue(decision.should_process)
        self.assertEqual(decision.reason, "tail_silence_detected")


class FilterResultTests(unittest.TestCase):
    def test_filters_short_or_filler_only_text(self):
        self.assertTrue(should_filter_asr_result("嗯啊"))
        self.assertTrue(should_filter_asr_result("哈"))

    def test_keeps_normal_sentence(self):
        self.assertFalse(should_filter_asr_result("今天下午两点开会"))


if __name__ == "__main__":
    unittest.main()
