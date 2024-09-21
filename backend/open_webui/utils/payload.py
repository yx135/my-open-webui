from open_webui.utils.task import prompt_template
from open_webui.utils.misc import (
    add_or_update_system_message,
)

from typing import Callable, Optional


# inplace function: form_data is modified
def apply_model_system_prompt_to_body(params: dict, form_data: dict, user) -> dict:
    system = params.get("system", None)
    if not system:
        return form_data

    if user:
        template_params = {
            "user_name": user.name,
            "user_location": user.info.get("location") if user.info else None,
        }
    else:
        template_params = {}
    system = prompt_template(system, **template_params)
    form_data["messages"] = add_or_update_system_message(
        system, form_data.get("messages", [])
    )
    return form_data


# inplace function: form_data is modified
def apply_model_params_to_body(
    params: dict, form_data: dict, mappings: dict[str, Callable]
) -> dict:
    if not params:
        return form_data

    for key, cast_func in mappings.items():
        if (value := params.get(key)) is not None:
            form_data[key] = cast_func(value)

    return form_data


# inplace function: form_data is modified
def apply_model_params_to_body_openai(params: dict, form_data: dict) -> dict:
    mappings = {
        "temperature": float,
        "top_p": float,
        "max_tokens": int,
        "frequency_penalty": float,
        "seed": lambda x: x,
        "stop": lambda x: [bytes(s, "utf-8").decode("unicode_escape") for s in x],
    }
    return apply_model_params_to_body(params, form_data, mappings)


def apply_model_params_to_body_ollama(params: dict, form_data: dict) -> dict:
    opts = [
        "temperature",
        "top_p",
        "seed",
        "mirostat",
        "mirostat_eta",
        "mirostat_tau",
        "num_ctx",
        "num_batch",
        "num_keep",
        "repeat_last_n",
        "tfs_z",
        "top_k",
        "min_p",
        "use_mmap",
        "use_mlock",
        "num_thread",
        "num_gpu",
    ]
    mappings = {i: lambda x: x for i in opts}
    form_data = apply_model_params_to_body(params, form_data, mappings)

    name_differences = {
        "max_tokens": "num_predict",
        "frequency_penalty": "repeat_penalty",
    }

    for key, value in name_differences.items():
        if (param := params.get(key, None)) is not None:
            form_data[value] = param

    return form_data


def convert_payload_openai_to_ollama(openai_payload: dict) -> dict:
    """
    Converts a payload formatted for OpenAI's API to be compatible with Ollama's API endpoint for chat completions.

    Args:
        openai_payload (dict): The payload originally designed for OpenAI API usage.

    Returns:
        dict: A modified payload compatible with the Ollama API.
    """
    ollama_payload = {}

    # Mapping basic model and message details
    ollama_payload["model"] = openai_payload.get("model")
    ollama_payload["messages"] = openai_payload.get("messages")
    ollama_payload["stream"] = openai_payload.get("stream", False)

    # If there are advanced parameters in the payload, format them in Ollama's options field
    ollama_options = {}

    # Handle parameters which map directly
    for param in ["temperature", "top_p", "seed"]:
        if param in openai_payload:
            ollama_options[param] = openai_payload[param]

    # Mapping OpenAI's `max_tokens` -> Ollama's `num_predict`
    if "max_completion_tokens" in openai_payload:
        ollama_options["num_predict"] = openai_payload["max_completion_tokens"]
    elif "max_tokens" in openai_payload:
        ollama_options["num_predict"] = openai_payload["max_tokens"]

    # Handle frequency / presence_penalty, which needs renaming and checking
    if "frequency_penalty" in openai_payload:
        ollama_options["repeat_penalty"] = openai_payload["frequency_penalty"]

    if "presence_penalty" in openai_payload and "penalty" not in ollama_options:
        # We are assuming presence penalty uses a similar concept in Ollama, which needs custom handling if exists.
        ollama_options["new_topic_penalty"] = openai_payload["presence_penalty"]

    # Add options to payload if any have been set
    if ollama_options:
        ollama_payload["options"] = ollama_options

    return ollama_payload
