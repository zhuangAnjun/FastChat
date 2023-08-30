"""Call API providers."""

import os
import random
import time

from fastchat.utils import build_logger
from fastchat.constants import WORKER_API_TIMEOUT


logger = build_logger("gradio_web_server", "gradio_web_server.log")


def openai_api_stream_iter(
    model_name,
    messages,
    temperature,
    top_p,
    max_new_tokens,
    api_base=None,
    api_key=None,
):
    import openai

    openai.api_base = api_base or "https://api.openai.com/v1"
    openai.api_key = api_key or os.environ["OPENAI_API_KEY"]

    # Make requests
    gen_params = {
        "model": model_name,
        "prompt": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_new_tokens": max_new_tokens,
    }
    logger.info(f"==== request ====\n{gen_params}")

    engine = ""
    if (model_name == "gpt-3.5-turbo"):
        engine = "FutuTurbo0301"
        openai.api_base = os.getenv("OPENAI_API_BASE_GPT35")
        openai.api_key = os.getenv("OPENAI_API_KEY_GPT35")
        openai.api_version = os.getenv("OPENAI_API_VERSION_GPT35")
        openai.api_type = os.getenv("OPENAI_API_TYPE_GPT35")
        engine = os.getenv("OPENAI_ENGINE_GPT35")

    elif (model_name == "gpt-4"):
        openai.api_base = os.getenv("OPENAI_API_BASE_GPT4")
        openai.api_key = os.getenv("OPENAI_API_KEY_GPT4")
        openai.api_version = os.getenv("OPENAI_API_VERSION_GPT4")
        openai.api_type = os.getenv("OPENAI_API_TYPE_GPT4")
        engine = os.getenv("OPENAI_ENGINE_GPT4")

    res = openai.ChatCompletion.create(
        model=model_name,
        engine=engine,
        messages=messages,
        temperature=temperature,
        max_tokens=max_new_tokens,
        stream=True,
    )
    text = ""
    for chunk in res:
        text += chunk["choices"][0]["delta"].get("content", "")
        data = {
            "text": text,
            "error_code": 0,
        }
        yield data


def anthropic_api_stream_iter(model_name, prompt, temperature, top_p, max_new_tokens):
    import anthropic

    c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Make requests
    gen_params = {
        "model": model_name,
        "prompt": prompt,
        "temperature": temperature,
        "top_p": top_p,
        "max_new_tokens": max_new_tokens,
    }
    logger.info(f"==== request ====\n{gen_params}")

    res = c.completions.create(
        prompt=prompt,
        stop_sequences=[anthropic.HUMAN_PROMPT],
        max_tokens_to_sample=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        model=model_name,
        stream=True,
    )
    text = ""
    for chunk in res:
        text += chunk.completion
        data = {
            "text": text,
            "error_code": 0,
        }
        yield data


def init_palm_chat(model_name):
    import vertexai  # pip3 install google-cloud-aiplatform
    from vertexai.preview.language_models import ChatModel

    project_id = os.environ["GCP_PROJECT_ID"]
    location = "us-central1"
    vertexai.init(project=project_id, location=location)

    chat_model = ChatModel.from_pretrained(model_name)
    chat = chat_model.start_chat(examples=[])
    return chat


def palm_api_stream_iter(chat, message, temperature, top_p, max_new_tokens):
    parameters = {
        "temperature": temperature,
        "top_p": top_p,
        "max_output_tokens": max_new_tokens,
    }
    gen_params = {
        "model": "palm-2",
        "prompt": message,
    }
    gen_params.update(parameters)
    logger.info(f"==== request ====\n{gen_params}")

    response = chat.send_message(message, **parameters)
    content = response.text

    pos = 0
    while pos < len(content):
        # This is a fancy way to simulate token generation latency combined
        # with a Poisson process.
        pos += random.randint(10, 20)
        time.sleep(random.expovariate(50))
        data = {
            "text": content[:pos],
            "error_code": 0,
        }
        yield data
