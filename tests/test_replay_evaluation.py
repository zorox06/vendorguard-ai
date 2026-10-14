"""Integration tests for Research Replay Evaluation Harness."""

from research.replay.replay_engine import ChronologicalReplayHarness


def test_chronological_replay_execution():
    harness = ChronologicalReplayHarness()
    results = harness.run_replay()

    assert "baselines" in results
    baselines = results["baselines"]
    assert len(baselines) == 5

    systems = [b["system"] for b in baselines]
    assert systems == ["B0", "B1", "B2", "P1", "P2"]

    for b in baselines:
        assert 0.0 <= b["alert_episode_precision"] <= 1.0
        assert 0.0 <= b["incident_recall"] <= 1.0
        assert b["warning_lead_time_days"] >= 0.0
        assert b["false_alert_burden"] >= 0.0
        assert 0.0 <= b["actionable_recall"] <= 1.0
