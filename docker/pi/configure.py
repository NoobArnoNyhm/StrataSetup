"""Configure Pi for the single model served by the local Strata container."""

import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


class ConfigurationError(ValueError):
    pass


def context_tokens(value):
    match = re.fullmatch(r"([1-9][0-9]*)([kK]?)", value)
    if not match:
        raise ConfigurationError("STRATA_CONTEXT muss eine Tokenzahl oder z.B. 32k sein.")
    tokens = int(match[1]) * (1024 if match[2] else 1)
    if not 8192 <= tokens <= 1048576:
        raise ConfigurationError("STRATA_CONTEXT muss zwischen 8192 und 1048576 liegen.")
    return tokens


def discover_model(base_url, key, wait_seconds=60):
    parsed = urllib.parse.urlsplit(base_url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/v1"
    ):
        raise ConfigurationError("STRATA_BASE_URL muss ein API-Endpunkt mit /v1 ohne Zugangsdaten sein.")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    # Internal traffic must not send the API key through a host-configured proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            with opener.open(request, timeout=min(5, max(0.1, deadline - time.monotonic()))) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as error:
            if error.code < 500:
                raise ConfigurationError(f"Strata lehnt die Modellabfrage ab: HTTP {error.code}.") from error
            message = f"HTTP {error.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            message = type(error).__name__
        except (json.JSONDecodeError, UnicodeError) as error:
            raise ConfigurationError("Strata liefert kein gueltiges Modell-JSON.") from error
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ConfigurationError(f"Strata nach {wait_seconds}s nicht erreichbar ({message}).")
        print(f"Warte auf Strata ({message}) ...", file=sys.stderr, flush=True)
        time.sleep(min(2, remaining))

    models = payload.get("data") if isinstance(payload, dict) else None
    if (
        not isinstance(models, list)
        or len(models) != 1
        or not isinstance(models[0], dict)
        or not isinstance(models[0].get("id"), str)
        or not models[0]["id"].strip()
    ):
        raise ConfigurationError("Strata muss genau eine eindeutige Modell-ID in data[].id liefern.")
    return models[0]["id"]


def read_object(path):
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ConfigurationError(f"Ungueltige JSON-Datei: {path}") from error
    if not isinstance(value, dict):
        raise ConfigurationError(f"JSON-Objekt erwartet: {path}")
    return value


def object_field(value, key):
    if key not in value:
        value[key] = {}
    if not isinstance(value[key], dict):
        raise ConfigurationError(f"Konfigurationsfeld '{key}' muss ein Objekt sein.")
    return value[key]


def atomic_write(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(agent_dir, base_url, model_id, context, vision):
    models_path = agent_dir / "models.json"
    settings_path = agent_dir / "settings.json"
    models = read_object(models_path)
    settings = read_object(settings_path)
    provider = object_field(object_field(models, "providers"), "strata")
    compat = object_field(provider, "compat")
    compaction = object_field(settings, "compaction")

    # These compatibility and compaction values follow Strata v0.2.17's pi template.
    provider.update(
        baseUrl=base_url.rstrip("/"),
        api="openai-completions",
        apiKey="$STRATA_API_KEY",
        models=[{
            "id": model_id,
            "name": "Qwen3.8-Flash-Next (Strata, local)",
            "reasoning": True,
            "input": ["text"] if vision == "off" else ["text", "image"],
            "contextWindow": context,
            "maxTokens": max(4096, context // 8),
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        }],
    )
    compat.update(supportsDeveloperRole=False, supportsReasoningEffort=False)
    compact_at = max(15000, int((context - 4096) * 15000 / (32768 - 4096)))
    # At small custom windows, always leave room for the summarising request.
    compact_at = min(compact_at, context // 2)
    compaction.update(
        enabled=True, reserveTokens=max(1024, context - compact_at),
        keepRecentTokens=min(4000, compact_at // 2),
    )
    settings.update(defaultProvider="strata", defaultModel=model_id)
    settings.setdefault("defaultThinkingLevel", "medium")
    agent_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(models_path, models)
    atomic_write(settings_path, settings)


def main():
    try:
        key = os.environ.get("STRATA_API_KEY", "")
        if len(key) < 16 or "\r" in key or "\n" in key:
            raise ConfigurationError("STRATA_API_KEY fehlt, ist zu kurz oder enthaelt Zeilenumbrueche.")
        context = context_tokens(os.environ.get("STRATA_CONTEXT", "32k"))
        vision = os.environ.get("STRATA_VISION", "off")
        if vision not in ("off", "on", "gpu", "cpu"):
            raise ConfigurationError("STRATA_VISION muss off, on, gpu oder cpu sein.")
        base_url = os.environ.get("STRATA_BASE_URL", "http://strata:8080/v1")
        agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi" / "agent")))
        model_id = discover_model(base_url, key)
        configure(agent_dir, base_url, model_id, context, vision)
        print("Pi fuer Strata konfiguriert; Provider und Modell sind als Standard gesetzt.")
        return 0
    except (ConfigurationError, OSError) as error:
        print(f"Pi-Konfiguration fehlgeschlagen: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
