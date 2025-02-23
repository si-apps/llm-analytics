import pytest

from utils import init_env_from_file, invoke_llm, init_logging


@pytest.fixture(autouse=True)
def set_logging():
    init_logging()

@pytest.fixture()
def set_aws_creds():
    init_env_from_file("aws.env.list")

@pytest.fixture()
def set_gemini_api_key():
    init_env_from_file("google.env.list")



@pytest.mark.parametrize("model_id", ["anthropic.claude-instant-v1", "ai21.jamba-instruct-v1:0"])
def test_connect_to_bedrock(model_id: str, set_aws_creds):
    question = "What is the capital of Japan?"
    answer = invoke_llm(question, model_id=model_id)
    assert "Tokyo" in answer

@pytest.mark.parametrize("model_id", ["gemini-pro", "gemini-1.5-flash", "gemini-2.0-flash"])
def test_connect_to_gemini(model_id: str, set_gemini_api_key):
    question = "What is the capital of Japan?"
    answer = invoke_llm(question, model_id=model_id)
    assert "Tokyo" in answer

