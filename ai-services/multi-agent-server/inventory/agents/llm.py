import os

from openai import OpenAI

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=TIMEOUT_SECONDS, max_retries=0)


def call_model(model, system_prompt, user_prompt, max_tokens=180):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()
