"""Minimal Ollama client. Configure OLLAMA_URL and OLLAMA_MODEL if needed."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def generate_response(prompt: str) -> str:
    base_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": "json"}).encode("utf-8")
    request = Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Ollama returned HTTP {exc.code}. Check that the model is installed and the server is running.") from exc
    except URLError as exc:
        raise RuntimeError("Cannot reach Ollama. Start Ollama and confirm the local endpoint is available.") from exc
    except TimeoutError as exc:
        raise RuntimeError("Ollama timed out while generating the response.") from exc
    text = result.get("response")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Ollama returned an empty response.")
    return text
