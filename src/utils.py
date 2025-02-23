import json
import logging
import os
from logging.config import fileConfig
from pathlib import Path

_PROJECT_FOLDER = Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute()


def get_project_folder() -> str:
    return str(_PROJECT_FOLDER)


def init_logging():
    fileConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logging.conf"))
    logging.info("Logging initialized")


def init_env_from_file(file_name: str):
    full_file_name = os.path.join(get_project_folder(), "config", file_name)
    if os.path.exists(full_file_name):
        logging.info(f"Going to set env variables from file: {full_file_name}")
        with open(full_file_name) as f:
            for line in f:
                key, value = line.strip().split("=")
                os.environ[key] = value

def _get_default_model_id() -> str:
    if "MODEL_ID" in os.environ and os.environ["MODEL_ID"] != "":
        return os.environ["MODEL_ID"]
    elif ("ENV" in os.environ and "aws" in os.environ["ENV"]) or \
          "AWS_ACCESS_KEY_ID" in os.environ:
        return "anthropic.claude-instant-v1"
    elif ("ENV" in os.environ and "google" in os.environ["ENV"]) or \
            "GEMINI_API_KEY" in os.environ:
        return "gemini-2.0-flash"
    else:
        raise ValueError("No default model_id found")

def invoke_llm(prompt: str, model_id: str = None) -> str:
    if model_id is None or model_id == "":
        model_id = _get_default_model_id()
    if "gemini" in model_id:
        return _invoke_gemini_model(prompt, model_id)
    elif "jamba" in model_id or "claude" in model_id:
        return _invoke_bedrock_model(prompt, model_id)
    else:
        raise ValueError(f"Unknown model_id: {model_id}")

def _invoke_gemini_model(prompt: str, model_id: str) -> str:
    api_key = os.environ["GEMINI_API_KEY"]
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    response = model.generate_content(prompt)
    return response.text


def _invoke_bedrock_model(prompt: str, model_id: str) -> str:
    logging.info(f"Going to invoke LLM. Model ID: {model_id}")
    import boto3
    bedrock_client = boto3.client(service_name='bedrock-runtime')
    response = bedrock_client.invoke_model(
        body=_format_model_body(prompt, model_id),
        modelId=model_id,
    )
    response_json = json.loads(response.get("body").read())
    response_text = _get_response_content(response_json, model_id)
    logging.info(f"Got response from LLM. Response length: {len(response_text)}")
    return response_text

def _format_model_body(prompt: str, model_id: str) -> str:
    if "claude" in model_id:
        body = {
            'prompt': f"\n\nHuman: {prompt}\nAssistant:",
            'max_tokens_to_sample': 200,
            "temperature": 0.0,
        }
    elif "jamba" in model_id:
        body = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a SQL generator helper"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "n": 1
        }
    else:
        raise ValueError(f"Unknown model_id: {model_id}")
    return json.dumps(body)


def _get_response_content(response_json: dict, model_id: str) -> str:
    if "claude" in model_id:
        return response_json["completion"]
    elif "jamba" in model_id:
        return response_json["choices"][0]["message"]["content"]
    else:
        raise ValueError(f"Unknown model_id: {model_id}")

