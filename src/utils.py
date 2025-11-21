import http.client
import json
import logging
import os
from logging.config import fileConfig
from pathlib import Path
from typing import Optional

from boto3.session import Session
from botocore.config import Config

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
        return "us.anthropic.claude-haiku-4-5-20251001-v1:0"
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
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    conn = http.client.HTTPSConnection("generativelanguage.googleapis.com")
    endpoint = f"/v1beta/models/{model_id}:generateContent?key=" + api_key
    conn.request("POST", endpoint, body=json.dumps(data), headers=headers)
    response = conn.getresponse()
    result = response.read().decode()
    if response.status == 404:
        raise ValueError(
            f"Model '{model_id}' not found or not supported for generateContent. "
            "Check your model_id or use a supported Gemini model (e.g., 'gemini-2.0-pro', 'gemini-2.0-flash'). "
            f"Response: {result}"
        )
    json_data = json.loads(result)
    return json_data["candidates"][0]["content"]["parts"][0]["text"]


def _invoke_bedrock_model(prompt: str, model_id: str) -> str:
    logging.info(f"Going to invoke Bedrock LLM model. Model id: {model_id}")

    session = Session()
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    bedrock_client = session.client(
        service_name="bedrock-runtime",
        region_name=region,
        config=Config(read_timeout=300),
    )
    body_dict = _format_model_body(prompt, None, model_id)
    body_bytes = json.dumps(body_dict).encode("utf-8")
    response = bedrock_client.invoke_model(
        body=body_bytes,
        modelId=model_id,
    )
    return _get_response_content(json.loads(response.get("body").read()), model_id)

def _format_model_body(
    prompt: str, system_prompt: Optional[str], model_id: str
) -> dict:
    if system_prompt is None:
        system_prompt = "You are a SQL generator helper"
    if "claude" in model_id:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.0,
        }
    elif "jamba" in model_id:
        body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "n": 1,
        }
    else:
        raise ValueError(f"Unknown model_id: {model_id}")
    return body


def _get_response_content(response_json: dict, model_id: str) -> str:
    if "claude" in model_id:
        return response_json["content"][0]["text"]
    elif "jamba" in model_id:
        return response_json["choices"][0]["message"]["content"]
    else:
        raise ValueError(f"Unknown model_id: {model_id}")