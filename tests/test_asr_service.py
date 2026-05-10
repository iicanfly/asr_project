import unittest

from services.asr_service import (
    collapse_transcript_text,
    describe_tail_triggerable_speech,
    describe_usable_speech,
    extract_audio_features,
    has_tail_triggerable_speech,
    load_realtime_chunk_policy_overrides,
    is_effective_text_update,
    looks_like_sentence_boundary,
    RealtimeChunkPolicy,
    SegmentRewritePolicy,
    decide_segment_rewrite,
    decide_chunk_processing,
    decide_stop_flush,
    detect_silence,
    has_usable_speech,
    is_weak_background_audio,
    refine_asr_result_text,
    should_filter_asr_result,
)


def pcm_window(value: int, sample_count: int) -> bytes:
    return b"".join(value.to_bytes(2, "little", signed=True) for _ in range(sample_count))


def pcm_frames(frame_values, frame_size: int = 256) -> bytes:
    return b"".join(pcm_window(value, frame_size) for value in frame_values)


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
        audio_data = pcm_window(320, 16000 * 2)
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

    def test_brief_tail_speech_is_dropped_even_if_it_has_some_voiced_frames(self):
        policy = RealtimeChunkPolicy(
            min_audio_seconds=0.5,
            chunk_seconds=5.0,
            max_audio_seconds=30.0,
            tail_silence_bytes=4096,
        )
        brief_speech = pcm_frames(([320] * 6) + ([0] * 64))
        decision = decide_chunk_processing(brief_speech, policy)
        self.assertFalse(decision.should_process)
        self.assertTrue(decision.drop_buffer)
        self.assertEqual(decision.reason, "drop_brief_tail_speech")

    def test_weak_background_audio_is_dropped_at_chunk_boundary(self):
        policy = RealtimeChunkPolicy(chunk_seconds=1.0, max_audio_seconds=30.0)
        weak_audio = pcm_window(90, 16000 * 2)
        decision = decide_chunk_processing(weak_audio, policy)
        self.assertFalse(decision.should_process)
        self.assertTrue(decision.drop_buffer)
        self.assertEqual(decision.reason, "drop_weak_audio_at_chunk_duration")

    def test_stop_flush_processes_short_usable_tail(self):
        policy = RealtimeChunkPolicy(stop_flush_min_seconds=0.35)
        tail_audio = pcm_window(900, int(16000 * 0.45))
        decision = decide_stop_flush(tail_audio, policy)
        self.assertTrue(decision.should_process)
        self.assertEqual(decision.reason, "stop_flush_pending_audio")

    def test_stop_flush_drops_weak_tail(self):
        policy = RealtimeChunkPolicy(stop_flush_min_seconds=0.35)
        tail_audio = pcm_window(80, int(16000 * 0.45))
        decision = decide_stop_flush(tail_audio, policy)
        self.assertFalse(decision.should_process)
        self.assertTrue(decision.drop_buffer)
        self.assertEqual(decision.reason, "stop_flush_drop_weak_audio")

    def test_stop_flush_ignores_tiny_tail(self):
        policy = RealtimeChunkPolicy(stop_flush_min_seconds=0.35)
        tail_audio = pcm_window(1000, int(16000 * 0.2))
        decision = decide_stop_flush(tail_audio, policy)
        self.assertFalse(decision.should_process)
        self.assertEqual(decision.reason, "stop_flush_below_min_duration")


class RealtimePolicyOverrideTests(unittest.TestCase):
    def test_loads_global_realtime_policy_overrides(self):
        policy, overrides = load_realtime_chunk_policy_overrides(
            RealtimeChunkPolicy(),
            {
                "REALTIME_CHUNK_SECONDS": "6.5",
                "REALTIME_MIN_VOICED_DENSITY_FOR_SOFT_SPEECH": "0.32",
            },
        )
        self.assertEqual(policy.chunk_seconds, 6.5)
        self.assertEqual(policy.min_voiced_density_for_soft_speech, 0.32)
        self.assertEqual(overrides["chunk_seconds"], 6.5)
        self.assertEqual(overrides["min_voiced_density_for_soft_speech"], 0.32)

    def test_mode_specific_override_beats_global_override(self):
        policy, overrides = load_realtime_chunk_policy_overrides(
            RealtimeChunkPolicy(),
            {
                "REALTIME_CHUNK_SECONDS": "7.0",
                "ONLINE_REALTIME_CHUNK_SECONDS": "4.0",
            },
            mode_prefix="online",
        )
        self.assertEqual(policy.chunk_seconds, 4.0)
        self.assertEqual(overrides["chunk_seconds"], 4.0)


class AudioFeatureTests(unittest.TestCase):
    def test_feature_extraction_marks_speech_as_usable(self):
        policy = RealtimeChunkPolicy()
        speech_audio = pcm_window(900, 2048)
        features = extract_audio_features(speech_audio)
        self.assertTrue(has_usable_speech(features, policy))
        self.assertFalse(is_weak_background_audio(features, policy))

    def test_feature_extraction_marks_background_as_weak(self):
        policy = RealtimeChunkPolicy()
        weak_audio = pcm_window(60, 2048)
        features = extract_audio_features(weak_audio)
        self.assertFalse(has_usable_speech(features, policy))
        self.assertTrue(is_weak_background_audio(features, policy))

    def test_active_noise_without_voiced_presence_is_not_usable_speech(self):
        policy = RealtimeChunkPolicy(chunk_seconds=1.0)
        noisy_audio = pcm_window(150, 16000 * 2)
        features = extract_audio_features(noisy_audio)
        self.assertFalse(has_usable_speech(features, policy))
        self.assertEqual(describe_usable_speech(features, policy), "no_usable_speech")

        decision = decide_chunk_processing(noisy_audio, policy)
        self.assertFalse(decision.should_process)
        self.assertTrue(decision.drop_buffer)
        self.assertEqual(decision.reason, "drop_weak_audio_at_chunk_duration")

    def test_sustained_soft_speech_still_counts_as_usable(self):
        policy = RealtimeChunkPolicy()
        soft_speech_audio = pcm_frames(([240] * 22) + ([320] * 8) + ([0] * 120))
        features = extract_audio_features(soft_speech_audio)

        self.assertGreaterEqual(features.active_ratio, policy.min_active_ratio)
        self.assertLess(features.voiced_ratio, policy.min_voiced_ratio)
        self.assertTrue(has_usable_speech(features, policy))
        self.assertTrue(has_tail_triggerable_speech(features, policy))
        self.assertEqual(describe_usable_speech(features, policy), "sustained_soft_speech")
        self.assertEqual(describe_tail_triggerable_speech(features, policy), "tail_sustained_presence")

    def test_sparse_voiced_activity_does_not_trigger_soft_speech_fallback(self):
        policy = RealtimeChunkPolicy()
        sparse_voiced_audio = pcm_frames(([240] * 28) + ([320] * 6) + ([0] * 116))
        features = extract_audio_features(sparse_voiced_audio)

        self.assertGreaterEqual(features.active_ratio, policy.min_active_ratio)
        self.assertGreaterEqual(features.rms, policy.active_speech_rms_threshold)
        self.assertGreaterEqual(features.peak, policy.active_speech_peak_threshold)
        self.assertLess(features.voiced_density, policy.min_voiced_density_for_soft_speech)
        self.assertFalse(has_usable_speech(features, policy))
        self.assertEqual(describe_usable_speech(features, policy), "no_usable_speech")


class FilterResultTests(unittest.TestCase):
    def test_filters_short_or_filler_only_text(self):
        self.assertTrue(should_filter_asr_result("嗯"))
        self.assertTrue(should_filter_asr_result("嗯啊"))
        self.assertTrue(should_filter_asr_result("哈"))

    def test_keeps_normal_sentence(self):
        self.assertFalse(should_filter_asr_result("今天下午两点开会"))

    def test_trims_boundary_fillers_but_keeps_meaningful_content(self):
        self.assertEqual(refine_asr_result_text("嗯 今天开始"), "今天开始")
        self.assertEqual(refine_asr_result_text("啊好的"), "好的")
        self.assertEqual(refine_asr_result_text("你好啊"), "你好")
        self.assertFalse(should_filter_asr_result("嗯 今天开始"))
        self.assertFalse(should_filter_asr_result("啊好的"))

    def test_keeps_short_valid_phrases(self):
        self.assertFalse(should_filter_asr_result("好的"))
        self.assertFalse(should_filter_asr_result("可以"))
        self.assertFalse(should_filter_asr_result("那个我们开始吧"))


class TranscriptTextHeuristicTests(unittest.TestCase):
    def test_collapse_transcript_text_removes_spacing_and_punctuation(self):
        self.assertEqual(collapse_transcript_text("你好， 世界。"), "你好世界")

    def test_looks_like_sentence_boundary_prefers_complete_text(self):
        self.assertTrue(looks_like_sentence_boundary("今天的会议先到这里。"))
        self.assertTrue(looks_like_sentence_boundary("这个方案我们明天继续讨论", min_chars=6))
        self.assertFalse(looks_like_sentence_boundary("然后我们", min_chars=6))

    def test_effective_text_update_skips_noop_rewrite(self):
        self.assertFalse(is_effective_text_update("今天开始。", "今天开始"))
        self.assertFalse(is_effective_text_update("嗯 今天开始", "今天开始"))
        self.assertTrue(is_effective_text_update("今天开始", "今天开始讨论方案"))


class SegmentRewriteDecisionTests(unittest.TestCase):
    def test_emits_rewrite_after_enough_chunks_and_duration(self):
        decision = decide_segment_rewrite(
            segment_duration_seconds=6.5,
            segment_chunk_count=2,
            last_rewrite_chunk_count=0,
            latest_chunk_reason="chunk_duration_reached",
            current_segment_text="今天我们讨论一下发布计划",
            policy=SegmentRewritePolicy(),
        )
        self.assertTrue(decision.should_emit_rewrite)
        self.assertFalse(decision.should_finalize_segment)

    def test_tail_silence_can_finalize_segment(self):
        decision = decide_segment_rewrite(
            segment_duration_seconds=4.5,
            segment_chunk_count=2,
            last_rewrite_chunk_count=0,
            latest_chunk_reason="tail_silence_detected",
            current_segment_text="今天的讨论先到这里。",
            policy=SegmentRewritePolicy(),
        )
        self.assertTrue(decision.should_emit_rewrite)
        self.assertTrue(decision.should_finalize_segment)

    def test_tail_silence_does_not_finalize_short_incomplete_segment(self):
        decision = decide_segment_rewrite(
            segment_duration_seconds=4.5,
            segment_chunk_count=2,
            last_rewrite_chunk_count=0,
            latest_chunk_reason="tail_silence_detected",
            current_segment_text="然后我们",
            policy=SegmentRewritePolicy(),
        )
        self.assertFalse(decision.should_emit_rewrite)
        self.assertFalse(decision.should_finalize_segment)

    def test_waits_when_segment_is_too_short(self):
        decision = decide_segment_rewrite(
            segment_duration_seconds=2.0,
            segment_chunk_count=1,
            last_rewrite_chunk_count=0,
            latest_chunk_reason="waiting_for_more_audio",
            current_segment_text="开始了",
            policy=SegmentRewritePolicy(),
        )
        self.assertFalse(decision.should_emit_rewrite)
        self.assertFalse(decision.should_finalize_segment)


if __name__ == "__main__":
    unittest.main()
