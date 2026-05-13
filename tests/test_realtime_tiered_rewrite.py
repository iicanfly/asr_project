import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main
from services.asr_service import AudioFeatures, ChunkDecision


class RealtimeTieredRewriteTests(unittest.TestCase):
    def _build_session(self):
        return {
            "result_seq": 0,
            "chunk_seq": 0,
            "segment_seq": 0,
            "session_tag": "demo",
            "active_segment": None,
            "processing": False,
            "stop_requested": False,
            "last_audio_time": 0.0,
            "last_speech_time": 0.0,
            "last_idle_rewrite_audio_time": 0.0,
            "buffer": bytearray(),
        }

    def _build_chunk_decision(self, duration_seconds=2.5, reason="chunk_duration_reached"):
        return ChunkDecision(
            should_process=True,
            reason=reason,
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
        )

    def _build_features(
        self,
        *,
        rms=0.0035,
        peak=230,
        active_ratio=0.22,
        voiced_ratio=0.14,
        silence_ratio=0.78,
        max_active_run_seconds=0.1,
        max_voiced_run_seconds=0.07,
        duration_seconds=0.2,
    ):
        return AudioFeatures(
            duration_seconds=duration_seconds,
            rms=rms,
            peak=peak,
            active_ratio=active_ratio,
            voiced_ratio=voiced_ratio,
            silence_ratio=silence_ratio,
            frame_count=12,
            max_active_run_seconds=max_active_run_seconds,
            max_voiced_run_seconds=max_voiced_run_seconds,
        )

    def test_partial_updates_replace_prior_result(self):
        session = self._build_session()
        chunk_decision = self._build_chunk_decision()
        emitted_payloads = []

        def fake_emit(event_name, payload, to=None):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", side_effect=["重要约束", "基于事实总结"]), patch.object(main.socketio, "emit", side_effect=fake_emit):
            main.process_realtime_audio_chunk(session, "sid-1", b"\x01\x02" * 16000, chunk_decision)
            main.process_realtime_audio_chunk(session, "sid-1", b"\x03\x04" * 16000, chunk_decision)

        self.assertEqual(len(emitted_payloads), 2)
        self.assertEqual(emitted_payloads[0]["result_type"], "segment_partial")
        self.assertIsNone(emitted_payloads[0]["replace_target_id"])
        self.assertEqual(emitted_payloads[1]["result_type"], "segment_partial")
        self.assertEqual(emitted_payloads[1]["replace_target_id"], emitted_payloads[0]["result_id"])
        self.assertIn("重要约束", emitted_payloads[1]["text"])
        self.assertIn("基于事实总结", emitted_payloads[1]["text"])
        self.assertEqual(emitted_payloads[1]["stable_text"], "")
        self.assertEqual(emitted_payloads[1]["medium_text"], "")
        self.assertIn("重要约束", emitted_payloads[1]["partial_text"])

    def test_high_rewrite_commits_current_stage(self):
        session = self._build_session()
        active_segment = main.get_or_create_active_segment(session)
        active_segment["audio_buffer"].extend(b"\x01\x02" * 16000)
        active_segment["chunk_count"] = 12
        active_segment["duration_seconds"] = 30.0
        active_segment["stage_chunk_count"] = 12
        active_segment["stage_duration_seconds"] = 30.0
        active_segment["stage_display_text"] = "重要约束基于转写中的事实"
        active_segment["last_result_id"] = "demo_result_prev"
        active_segment["latest_display_text"] = "重要约束基于转写中的事实"
        active_segment["latest_result_type"] = "segment_partial"
        emitted_payloads = []

        def fake_emit(event_name, payload, to=None):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", return_value="重要约束基于转写中的事实进行总结和归纳"), patch.object(main.socketio, "emit", side_effect=fake_emit):
            emitted = main.emit_tiered_rewrite_if_needed(
                session,
                "sid-1",
                active_segment,
                self._build_chunk_decision(duration_seconds=30.0),
            )

        self.assertTrue(emitted)
        self.assertEqual(len(emitted_payloads), 1)
        self.assertEqual(emitted_payloads[0]["result_type"], "high_rewrite")
        self.assertEqual(emitted_payloads[0]["replace_target_id"], "demo_result_prev")
        self.assertIn("总结和归纳", emitted_payloads[0]["stable_text"])
        self.assertEqual(emitted_payloads[0]["medium_text"], "")
        self.assertEqual(emitted_payloads[0]["partial_text"], "")
        self.assertEqual(active_segment["stage_duration_seconds"], 0.0)
        self.assertEqual(active_segment["stage_display_text"], "")
        self.assertIn("总结和归纳", active_segment["stable_text"])

    def test_finalize_emits_high_rewrite_for_same_text_to_upgrade_level(self):
        session = self._build_session()
        active_segment = main.get_or_create_active_segment(session)
        active_segment["stage_display_text"] = "重要约束"
        active_segment["stage_duration_seconds"] = 4.0
        active_segment["chunk_count"] = 1
        active_segment["duration_seconds"] = 4.0
        active_segment["last_result_id"] = "demo_result_prev"
        active_segment["latest_display_text"] = "重要约束"
        active_segment["latest_result_type"] = "segment_partial"
        emitted_payloads = []

        def fake_emit(event_name, payload, to=None):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", return_value=""), patch.object(main.socketio, "emit", side_effect=fake_emit):
            emitted = main.emit_tiered_rewrite_if_needed(
                session,
                "sid-1",
                active_segment,
                self._build_chunk_decision(duration_seconds=4.0, reason="stop_recording_finalize_segment"),
                finalize_segment=True,
            )

        self.assertTrue(emitted)
        self.assertEqual(len(emitted_payloads), 1)
        self.assertEqual(emitted_payloads[0]["result_type"], "high_rewrite")
        self.assertEqual(emitted_payloads[0]["text"], "重要约束")
        self.assertEqual(emitted_payloads[0]["stable_text"], "重要约束")
        self.assertEqual(emitted_payloads[0]["medium_text"], "")
        self.assertEqual(emitted_payloads[0]["partial_text"], "")
        self.assertEqual(active_segment["stable_text"], "重要约束")
        self.assertEqual(active_segment["stage_duration_seconds"], 0.0)

    def test_partial_after_medium_keeps_medium_prefix_separate(self):
        session = self._build_session()
        active_segment = main.get_or_create_active_segment(session)
        active_segment["stage_display_text"] = "重要约束：基于转写中的事实进行总结和归纳。"
        active_segment["last_medium_text"] = "重要约束：基于转写中的事实进行总结和归纳。"
        active_segment["last_result_id"] = "demo_result_prev"
        active_segment["latest_display_text"] = active_segment["stage_display_text"]
        active_segment["latest_result_type"] = "medium_rewrite"
        chunk_decision = self._build_chunk_decision()
        emitted_payloads = []

        def fake_emit(event_name, payload, to=None):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", return_value="禁止编造"), patch.object(main.socketio, "emit", side_effect=fake_emit):
            main.process_realtime_audio_chunk(session, "sid-1", b"\x05\x06" * 16000, chunk_decision)

        self.assertEqual(len(emitted_payloads), 1)
        self.assertEqual(emitted_payloads[0]["result_type"], "segment_partial")
        self.assertEqual(emitted_payloads[0]["stable_text"], "")
        self.assertEqual(emitted_payloads[0]["medium_text"], "重要约束：基于转写中的事实进行总结和归纳。")
        self.assertIn("禁止编造", emitted_payloads[0]["partial_text"])

    def test_idle_timeout_triggers_high_rewrite_without_stop(self):
        session = self._build_session()
        active_segment = main.get_or_create_active_segment(session)
        active_segment["audio_buffer"].extend(b"\x01\x02" * 16000)
        active_segment["chunk_count"] = 4
        active_segment["duration_seconds"] = 9.5
        active_segment["stage_chunk_count"] = 4
        active_segment["stage_duration_seconds"] = 9.5
        active_segment["stage_display_text"] = "可以对已有信息进行合理扩充。"
        active_segment["last_result_id"] = "demo_result_prev"
        active_segment["latest_display_text"] = active_segment["stage_display_text"]
        active_segment["latest_result_type"] = "segment_partial"
        session["last_speech_time"] = 100.0
        session["last_audio_time"] = 109.5
        emitted_payloads = []

        def fake_emit(event_name, payload, to=None):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "IDLE_SEGMENT_SPLIT_SECONDS", 0.0), patch.object(main, "transcribe_realtime_chunk", return_value="可以对已有信息进行合理扩充。"), patch.object(main.socketio, "emit", side_effect=fake_emit):
            emitted = main.process_idle_realtime_session(session, "sid-1", now=111.0)

        self.assertTrue(emitted)
        self.assertEqual(len(emitted_payloads), 1)
        self.assertEqual(emitted_payloads[0]["result_type"], "high_rewrite")
        self.assertEqual(emitted_payloads[0]["processing_reason"], "idle_high_rewrite_timeout")
        self.assertEqual(emitted_payloads[0]["stable_text"], "可以对已有信息进行合理扩充。")
        self.assertEqual(emitted_payloads[0]["medium_text"], "")
        self.assertEqual(emitted_payloads[0]["partial_text"], "")
        self.assertEqual(active_segment["stage_duration_seconds"], 0.0)
        self.assertEqual(session["last_idle_rewrite_audio_time"], 100.0)

    def test_idle_segment_boundary_flushes_before_finalizing_current_segment(self):
        session = self._build_session()
        active_segment = main.get_or_create_active_segment(session)
        active_segment["stage_display_text"] = "第一段内容"
        active_segment["stage_duration_seconds"] = 4.0
        active_segment["chunk_count"] = 2
        active_segment["duration_seconds"] = 4.0
        active_segment["last_result_id"] = "demo_result_prev"
        active_segment["latest_display_text"] = "第一段内容"
        active_segment["latest_result_type"] = "segment_partial"
        session["last_speech_time"] = 100.0
        session["last_audio_time"] = 100.2
        call_order = []
        emitted_payloads = []

        def fake_flush(*args, **kwargs):
            call_order.append("flush")
            return False

        def fake_emit(event_name, payload, to=None):
            if event_name == "asr_result":
                call_order.append("emit")
                emitted_payloads.append(payload)

        with patch.object(main, "IDLE_SEGMENT_SPLIT_SECONDS", 2.0), patch.object(main, "flush_pending_realtime_buffer", side_effect=fake_flush), patch.object(main, "transcribe_realtime_chunk", return_value=""), patch.object(main.socketio, "emit", side_effect=fake_emit):
            emitted = main.process_idle_realtime_session(session, "sid-1", now=103.2)

        self.assertTrue(emitted)
        self.assertEqual(call_order, ["flush", "emit"])
        self.assertEqual(len(emitted_payloads), 1)
        self.assertEqual(emitted_payloads[0]["result_type"], "high_rewrite")
        self.assertEqual(emitted_payloads[0]["processing_reason"], "idle_segment_boundary_timeout")
        self.assertEqual(emitted_payloads[0]["text"], "第一段内容")
        self.assertIsNone(session["active_segment"])
        self.assertEqual(session["last_idle_rewrite_audio_time"], 100.0)

    def test_high_rewrite_starts_new_segment_after_stable_text_crosses_threshold(self):
        session = self._build_session()
        active_segment = main.get_or_create_active_segment(session)
        active_segment["audio_buffer"].extend(b"\x01\x02" * 16000)
        active_segment["chunk_count"] = 12
        active_segment["duration_seconds"] = 30.0
        active_segment["stage_chunk_count"] = 12
        active_segment["stage_duration_seconds"] = 30.0
        active_segment["stage_display_text"] = "我们需要基于事实做完整总结。"
        active_segment["last_result_id"] = "demo_result_prev"
        long_sentence = "这是一个已经经过高级回写确认的完整句子。" * 8
        emitted_payloads = []

        def fake_emit(event_name, payload, to=None):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", return_value=long_sentence), patch.object(main.socketio, "emit", side_effect=fake_emit), patch.object(main, "HIGH_REWRITE_SEGMENT_SPLIT_MIN_CHARS", 100):
            emitted = main.emit_tiered_rewrite_if_needed(
                session,
                "sid-1",
                active_segment,
                self._build_chunk_decision(duration_seconds=30.0),
            )

        self.assertTrue(emitted)
        self.assertEqual(len(emitted_payloads), 1)
        self.assertEqual(emitted_payloads[0]["result_type"], "high_rewrite")
        self.assertIsNone(session["active_segment"])

    def test_high_rewrite_does_not_split_when_sentence_boundary_is_incomplete(self):
        session = self._build_session()
        active_segment = main.get_or_create_active_segment(session)
        active_segment["audio_buffer"].extend(b"\x01\x02" * 16000)
        active_segment["chunk_count"] = 12
        active_segment["duration_seconds"] = 30.0
        active_segment["stage_chunk_count"] = 12
        active_segment["stage_duration_seconds"] = 30.0
        active_segment["stage_display_text"] = "当前段"
        active_segment["last_result_id"] = "demo_result_prev"
        unfinished_sentence = "我们需要继续推进这个方案的" * 12

        with patch.object(main, "transcribe_realtime_chunk", return_value=unfinished_sentence), patch.object(main.socketio, "emit", return_value=None), patch.object(main, "HIGH_REWRITE_SEGMENT_SPLIT_MIN_CHARS", 100):
            emitted = main.emit_tiered_rewrite_if_needed(
                session,
                "sid-1",
                active_segment,
                self._build_chunk_decision(duration_seconds=30.0),
            )

        self.assertTrue(emitted)
        self.assertIs(session["active_segment"], active_segment)
        self.assertGreaterEqual(len(active_segment["stable_text"]), len("当前段"))

    def test_meaningful_activity_rejects_weak_background_packet(self):
        features = self._build_features()

        with patch.object(main, "extract_audio_features", return_value=features), patch.object(main, "describe_usable_speech", return_value="strong_signal"), patch.object(main, "is_weak_background_audio", return_value=True):
            self.assertFalse(main.contains_meaningful_realtime_activity(b"\x01\x02" * 3200))

    def test_meaningful_activity_requires_voiced_density_for_soft_speech(self):
        features = self._build_features(
            active_ratio=0.3,
            voiced_ratio=0.06,
            max_active_run_seconds=0.12,
            max_voiced_run_seconds=0.06,
        )

        with patch.object(main, "extract_audio_features", return_value=features), patch.object(main, "describe_usable_speech", return_value="sustained_soft_speech"), patch.object(main, "is_weak_background_audio", return_value=False):
            self.assertFalse(main.contains_meaningful_realtime_activity(b"\x01\x02" * 3200))

class RealtimeRestartSessionTests(unittest.TestCase):
    def setUp(self):
        self._reset_session_manager_state()

    def tearDown(self):
        self._reset_session_manager_state()

    def _reset_session_manager_state(self):
        for sid in list(getattr(main.session_mgr, "_sessions", {}).keys()):
            main.cleanup_realtime_session(sid=sid, include_closing=True)
        for sid in list(getattr(main.session_mgr, "_closing_sessions", {}).keys()):
            main.cleanup_realtime_session(sid=sid, include_closing=True)
        main.session_mgr._recently_stopped.clear()

    def test_start_after_stop_requested_processing_creates_new_session_and_accepts_new_audio(self):
        sid = "sid-restart"
        old_session = main.session_mgr.get_or_create(sid)
        old_session["stop_requested"] = True
        old_session["processing"] = True
        old_session["buffer"].extend(b"old-buffer")

        with patch.object(main, "request", SimpleNamespace(sid=sid)):
            main.on_start_recording({"reason": "manual_start"})

        new_session = main.session_mgr.get(sid)
        self.assertIsNotNone(new_session)
        self.assertIsNot(new_session, old_session)
        self.assertNotEqual(new_session["session_tag"], old_session["session_tag"])
        self.assertIn(old_session, main.session_mgr._closing_sessions.get(sid, []))
        self.assertFalse(new_session["stop_requested"])

        with patch.object(main, "request", SimpleNamespace(sid=sid)), patch.object(main, "contains_meaningful_realtime_activity", return_value=False), patch.object(main, "try_drain_realtime_buffer", return_value=None):
            main.on_audio_stream(b"\x01\x02" * 128)

        self.assertGreater(len(new_session["buffer"]), 0)
        self.assertEqual(old_session["buffer"], bytearray(b"old-buffer"))

    def test_detached_stop_cleanup_does_not_remove_new_current_session(self):
        sid = "sid-cleanup"
        old_session = main.session_mgr.get_or_create(sid)
        old_session["stop_requested"] = True
        old_session["processing"] = True

        with patch.object(main, "request", SimpleNamespace(sid=sid)):
            main.on_start_recording({"reason": "manual_start"})

        new_session = main.session_mgr.get(sid)
        self.assertIsNot(new_session, old_session)

        old_session["processing"] = False
        with patch.object(main, "flush_pending_realtime_buffer", return_value=False) as mock_flush, patch.object(main, "finalize_active_segment_on_stop", return_value=False) as mock_finalize:
            main.drain_ready_realtime_buffer(old_session, sid, max_rounds=0)

        mock_flush.assert_called_once_with(old_session, sid, force_finalize_segment=True)
        mock_finalize.assert_called_once_with(old_session, sid)
        self.assertIs(main.session_mgr.get(sid), new_session)
        self.assertNotIn(old_session, main.session_mgr._closing_sessions.get(sid, []))


if __name__ == "__main__":
    unittest.main()
