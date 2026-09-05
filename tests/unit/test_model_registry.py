"""Model registry approval + champion/challenger."""

from services.quant import Approval, ModelCard, ModelRegistry, beats_baseline


def test_beats_baseline_margin():
    assert beats_baseline({"precision": 0.7}, {"precision": 0.6}, key="precision", margin=0.05)
    assert not beats_baseline({"precision": 0.62}, {"precision": 0.6}, key="precision", margin=0.05)


def test_champion_promotion_demotes_previous(tmp_path):
    reg = ModelRegistry(tmp_path / "models.jsonl")
    a = reg.register(ModelCard(name="logistic", metrics={"precision": 0.7}))
    b = reg.register(ModelCard(name="logistic-v2", metrics={"precision": 0.75}))

    reg.set_champion(a.model_id)
    assert reg.champion().model_id == a.model_id

    reg.set_approval(b.model_id, Approval.APPROVED)
    reg.set_champion(b.model_id)
    assert reg.champion().model_id == b.model_id
    assert reg.get(a.model_id).approval is Approval.APPROVED     # previous champion demoted


def test_registry_persists(tmp_path):
    path = tmp_path / "models.jsonl"
    reg = ModelRegistry(path)
    reg.register(ModelCard(name="m", metrics={"precision": 0.6}))
    assert path.exists()
