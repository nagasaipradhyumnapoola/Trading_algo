"""Job runner: retries and dead-letter queue."""

from services.ingestion import DeadLetterQueue, run_job


def test_retry_then_succeed():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")

    result = run_job("flaky", flaky, retries=3)
    assert result.success and result.attempts == 3


def test_dead_letter_on_exhaustion():
    dlq = DeadLetterQueue()

    def always_fail():
        raise ValueError("boom")

    result = run_job("bad", always_fail, retries=2, dlq=dlq)
    assert not result.success
    assert result.attempts == 3                 # 1 initial + 2 retries
    assert len(dlq) == 1 and dlq.items()[0].job == "bad"


def test_dead_letter_persists(tmp_path):
    dlq = DeadLetterQueue(tmp_path / "dlq.jsonl")
    run_job("bad", lambda: (_ for _ in ()).throw(RuntimeError("x")), retries=0, dlq=dlq)
    assert (tmp_path / "dlq.jsonl").exists()
