import unittest
from unittest.mock import patch

import main
from services.asr_service import ChunkDecision


class RealtimeTieredRewriteTests(unittest.TestCase):
    def _build_session(self):
        return {
            "result_seq": 0,
            "chunk_seq": 0,
            "segment_seq": 0,
            "session_tag": "demo",
            "active_segment": None,
            "processing": False,
        }

    def _build_chunk_decision(self, duration_seconds=2.5, reason="chunk_duration_reached"):
        return ChunkDecision(
            should_process=True,
            reason=reason,
            audio_duration_seconds=duration_seconds,
            trailing_silence_detected=False,
        )

    def test_partial_updates_replace_prior_result(self):
        session = self._build_session()
        chunk_decision = self._build_chunk_decision()
        emitted_payloads = []

        def fake_emit(event_name, payload):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", side_effect=["重要约束", "基于事实总结"]), patch.object(main, "emit", side_effect=fake_emit):
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

        def fake_emit(event_name, payload):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", return_value="重要约束基于转写中的事实进行总结和归纳"), patch.object(main, "emit", side_effect=fake_emit):
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

        def fake_emit(event_name, payload):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", return_value=""), patch.object(main, "emit", side_effect=fake_emit):
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

        def fake_emit(event_name, payload):
            if event_name == "asr_result":
                emitted_payloads.append(payload)

        with patch.object(main, "transcribe_realtime_chunk", return_value="禁止编造"), patch.object(main, "emit", side_effect=fake_emit):
            main.process_realtime_audio_chunk(session, "sid-1", b"\x05\x06" * 16000, chunk_decision)

        self.assertEqual(len(emitted_payloads), 1)
        self.assertEqual(emitted_payloads[0]["result_type"], "segment_partial")
        self.assertEqual(emitted_payloads[0]["stable_text"], "")
        self.assertEqual(emitted_payloads[0]["medium_text"], "重要约束：基于转写中的事实进行总结和归纳。")
        self.assertIn("禁止编造", emitted_payloads[0]["partial_text"])


if __name__ == "__main__":
    unittest.main()
