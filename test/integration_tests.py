import pytest

from utils import init_creds_from_file, invoke_llm, init_logging


@pytest.fixture(autouse=True)
def set_evn(monkeypatch):
    init_logging()
    init_creds_from_file()


@pytest.mark.parametrize("model_id", ["anthropic.claude-instant-v1", "ai21.jamba-instruct-v1:0"])
def test_connect_to_bedrock(model_id: str):
    question = "What is the capital of Japan?"
    answer = invoke_llm(question, model_id=model_id)
    assert "Tokyo" in answer
