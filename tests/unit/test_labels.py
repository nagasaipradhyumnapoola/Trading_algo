"""Fixed outcome labels."""

from datetime import date

from services.evaluation import LabelConfig, label_dataset, label_signal
from services.evaluation.backtest import Outcome
from services.ingestion import Bar, InMemoryBarRepository


def _bar(repo, iid, d, o, h, low, c):
    repo.upsert(Bar(instrument_id=iid, session_date=d, open=o, high=h, low=low,
                    close=c, volume=1000, source="syn"))


def _repo():
    repo = InMemoryBarRepository()
    # TGT: next open 100, then a bar hitting target (+6%)
    _bar(repo, "TGT", date(2026, 1, 1), 100, 101, 99, 100)
    _bar(repo, "TGT", date(2026, 1, 2), 100, 108, 99, 107)
    # STP: next open 100, then a bar hitting stop (-3%)
    _bar(repo, "STP", date(2026, 1, 1), 100, 101, 99, 100)
    _bar(repo, "STP", date(2026, 1, 2), 100, 101, 96, 98)
    return repo


def test_target_labels_one():
    lbl = label_signal("TGT", date(2026, 1, 1), _repo(), LabelConfig())
    assert lbl.y == 1 and lbl.outcome is Outcome.TARGET and lbl.realized_net > 0
    assert lbl.label_version == "lbl-0.1"


def test_stop_labels_zero():
    lbl = label_signal("STP", date(2026, 1, 1), _repo(), LabelConfig())
    assert lbl.y == 0 and lbl.outcome is Outcome.STOP and lbl.realized_net < 0


def test_label_dataset():
    labels = label_dataset([("TGT", date(2026, 1, 1)), ("STP", date(2026, 1, 1))], _repo())
    assert [l.y for l in labels] == [1, 0]
