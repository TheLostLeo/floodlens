from enum import StrEnum


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_DATA = "waiting_for_data"
    COMPLETE = "complete"
    FAILED = "failed"


ALLOWED_TRANSITIONS = {
    AnalysisStatus.QUEUED: {AnalysisStatus.RUNNING, AnalysisStatus.FAILED},
    AnalysisStatus.RUNNING: {AnalysisStatus.WAITING_FOR_DATA, AnalysisStatus.COMPLETE, AnalysisStatus.FAILED},
    AnalysisStatus.WAITING_FOR_DATA: {AnalysisStatus.QUEUED},
    AnalysisStatus.COMPLETE: set(),
    AnalysisStatus.FAILED: set(),
}


def can_transition(current: AnalysisStatus, target: AnalysisStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]
