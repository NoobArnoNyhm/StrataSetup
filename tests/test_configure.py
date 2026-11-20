from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

from configure import ConfigurationError, configure, context_tokens, discover_model


KEY = "test-only-local-key-not-a-secret"
MODEL = "fixture-qwen"


@contextmanager
def api_server(payload=None):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if self.headers.get("Authorization") != f"Bearer {KEY}":
                self.send_error(401)
                return
            body = json.dumps(payload if payload is not None else {"data": [{"id": MODEL}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            if len(requests) == 1:
                delta = {
                    "role": "assistant",
                    "tool_calls": [{
                        "index": 0, "id": "call_fixture", "type": "function",
                        "function": {
                            "name": "write",
                            "arguments": json.dumps({"path": "result.txt", "content": "LOCAL_TOOL_OK\n"}),
                        },
                    }],
                }
                reason = "tool_calls"
            else:
                delta = {"role": "assistant", "content": "LOCAL_STREAM_OK"}
                reason = "stop"
            for content, finish in ((delta, None), ({}, reason)):
                chunk = {
                    "id": "chatcmpl-fixture", "object": "chat.completion.chunk",
                    "created": 1, "model": MODEL,
                    "choices": [{"index": 0, "delta": content, "finish_reason": finish}],
                }
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class ConfigurationTests(unittest.TestCase):
    def test_discovers_exact_id_and_rejects_bad_auth(self):
        with api_server() as (url, _):
            self.assertEqual(discover_model(url, KEY), MODEL)
            with self.assertRaisesRegex(ConfigurationError, "HTTP 401"):
                discover_model(url, "wrong-key", wait_seconds=0)

    def test_rejects_ambiguous_or_malformed_model_catalog(self):
        for payload in (
            {"data": []},
            {"data": [{"id": "a"}, {"id": "b"}]},
            {"data": [{"id": ""}]},
            {"data": ["model"]},
            [],
        ):
            with self.subTest(payload=payload), api_server(payload) as (url, _):
                with self.assertRaisesRegex(ConfigurationError, "eindeutige Modell-ID"):
                    discover_model(url, KEY)

    def test_unreachable_server_has_a_bounded_failure(self):
        with self.assertRaisesRegex(ConfigurationError, "nicht erreichbar"):
            discover_model("http://127.0.0.1:1/v1", KEY, wait_seconds=0)

    def test_context_is_explicit_and_credentials_cannot_be_embedded_in_url(self):
        self.assertEqual(context_tokens("32k"), 32768)
        self.assertEqual(context_tokens("65536"), 65536)
        for value in ("0", "4k", "32gb", "-1", "2000k"):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                context_tokens(value)
        with self.assertRaises(ConfigurationError):
            discover_model("http://user:password@localhost/v1", KEY)

    def test_preserves_other_settings_and_sessions_across_reconfiguration(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = Path(directory)
            (agent / "models.json").write_text(json.dumps({"providers": {"other": {"api": "custom"}}}))
            (agent / "settings.json").write_text(json.dumps({
                "theme": "light", "defaultThinkingLevel": "low",
                "compaction": {"customOption": 7},
            }))
            session = agent / "session.jsonl"
            session.write_text("keep this session")
            configure(agent, "http://strata:8080/v1", MODEL, 32768, "off")
            first = (agent / "models.json").read_bytes()
            configure(agent, "http://strata:8080/v1", MODEL, 32768, "off")
            self.assertEqual(first, (agent / "models.json").read_bytes())
            models = json.loads(first)
            settings = json.loads((agent / "settings.json").read_text())
            self.assertEqual(models["providers"]["other"]["api"], "custom")
            provider = models["providers"]["strata"]
            self.assertEqual(provider["apiKey"], "$STRATA_API_KEY")
            self.assertEqual(provider["models"][0]["id"], MODEL)
            self.assertEqual(provider["models"][0]["contextWindow"], 32768)
            self.assertEqual(provider["models"][0]["maxTokens"], 4096)
            self.assertEqual(settings["defaultModel"], MODEL)
            self.assertEqual(settings["defaultThinkingLevel"], "low")
            self.assertEqual(settings["theme"], "light")
            self.assertEqual(settings["compaction"]["customOption"], 7)
            self.assertEqual(settings["compaction"]["reserveTokens"], 17768)
            self.assertEqual(session.read_text(), "keep this session")

    def test_invalid_existing_settings_leave_models_untouched(self):
        for settings in ('{"compaction": []}', '{"broken":', '[]'):
            with self.subTest(settings=settings), tempfile.TemporaryDirectory() as directory:
                agent = Path(directory)
                original = '{"providers": {"other": {}}}'
                (agent / "models.json").write_text(original)
                (agent / "settings.json").write_text(settings)
                with self.assertRaises(ConfigurationError):
                    configure(agent, "http://strata:8080/v1", MODEL, 32768, "off")
                self.assertEqual((agent / "models.json").read_text(), original)
                self.assertEqual((agent / "settings.json").read_text(), settings)

    def test_entrypoint_initializes_and_invalid_json_prevents_readiness(self):
        with tempfile.TemporaryDirectory() as directory, api_server() as (url, _):
            agent = Path(directory)
            env = dict(
                os.environ, PI_CODING_AGENT_DIR=directory,
                STRATA_BASE_URL=url, STRATA_API_KEY=KEY,
                STRATA_CONTEXT="32k", STRATA_VISION="off",
            )
            command = ["/opt/pi/entrypoint.sh", "sh", "-c", "test -f /tmp/pi-configured"]
            result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((agent / "settings.json").read_text())["defaultModel"], MODEL)
            (agent / "settings.json").write_text("invalid json")
            result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Ungueltige JSON-Datei", result.stderr)
            self.assertFalse(Path("/tmp/pi-configured").exists())

    def test_real_pi_uses_generated_defaults_streaming_and_a_write_tool(self):
        with tempfile.TemporaryDirectory() as directory, api_server() as (url, requests):
            work = Path(directory)
            agent = work / "agent"
            configure(agent, url, MODEL, 32768, "off")
            env = dict(os.environ, PI_CODING_AGENT_DIR=str(agent), STRATA_API_KEY=KEY)
            result = subprocess.run(
                ["pi", "--print", "--no-session", "--no-extensions", "--no-skills",
                 "--no-prompt-templates", "--tools", "write", "--thinking", "off",
                 "Write result.txt, then report the result."],
                cwd=work, env=env, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("LOCAL_STREAM_OK", result.stdout)
            self.assertEqual((work / "result.txt").read_text(), "LOCAL_TOOL_OK\n")
            self.assertEqual(len(requests), 2)
            for request in requests:
                self.assertEqual(request["path"], "/v1/chat/completions")
                self.assertEqual(request["auth"], f"Bearer {KEY}")
                self.assertEqual(request["body"]["model"], MODEL)
                self.assertTrue(request["body"]["stream"])
            self.assertTrue(any(message["role"] == "tool" for message in requests[1]["body"]["messages"]))


if __name__ == "__main__":
    unittest.main()
