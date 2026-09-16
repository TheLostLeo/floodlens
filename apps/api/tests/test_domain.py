from app.domain import AnalysisStatus, can_transition


def test_waiting_can_be_requeued_but_terminal_states_cannot():
    assert can_transition(AnalysisStatus.QUEUED, AnalysisStatus.RUNNING)
    assert can_transition(AnalysisStatus.RUNNING, AnalysisStatus.WAITING_FOR_DATA)
    assert not can_transition(AnalysisStatus.WAITING_FOR_DATA, AnalysisStatus.COMPLETE)
    assert can_transition(AnalysisStatus.WAITING_FOR_DATA, AnalysisStatus.QUEUED)
    assert not can_transition(AnalysisStatus.COMPLETE, AnalysisStatus.QUEUED)
