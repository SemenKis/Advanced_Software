import os
import requests


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)


def generate_response(prompt):
    url = f"{OLLAMA_URL}/api/generate"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        return result.get(
            "response",
            "No response returned by the AI model."
        )

    except requests.RequestException as error:
        raise RuntimeError(
            f"Unable to communicate with Ollama: {error}"
        )