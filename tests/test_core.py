import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("translate_core", Path(__file__).parents[1] / "core.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.seen.append((self.path, self.headers.get("Authorization"), None))
        if self.path == "/prefix/v1/models":
            self.respond(200, {"data": [{"id": "model-b"}, {"id": "model-a"}, {"id": "model-a"}]})
        else:
            self.respond(404, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.seen.append((self.path, self.headers.get("Authorization"), body))
        self.respond(200, {"choices": [{"message": {"content": "<think>private</think>red dress, standing"}, "finish_reason": "stop"}]})

    def respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Handler.seen.clear()

    def args(self, **updates):
        args = dict(text="穿红裙站立的人", base_url=self.url, api_key="test-only", model="model-a", mode="tags", source_language="auto", target_language="English")
        args.update(updates)
        return args

    def test_url_normalization(self):
        cases = {
            "example.com": "https://example.com/v1/chat/completions",
            "https://example.com/v1/": "https://example.com/v1/chat/completions",
            "https://example.com/api/v2/chat/completions/": "https://example.com/api/v2/chat/completions",
            "https://example.com/api/v2/models": "https://example.com/api/v2/chat/completions",
            "localhost:1234": "http://localhost:1234/v1/chat/completions",
            "https://example.com/chat/completions": "https://example.com/chat/completions",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(core.endpoints(url, "chat")[0], expected)

    def test_bad_urls(self):
        for value in ("", "file:///x", "https://user:secret@host", "https://host/?key=secret"):
            with self.assertRaises(ValueError):
                core.endpoints(value, "models")

    def test_models_fallback_and_auth(self):
        self.assertEqual(core.fetch_models(self.url + "/prefix", "test-only"), ["model-a", "model-b"])
        self.assertEqual([x[0] for x in Handler.seen], ["/prefix/models", "/prefix/v1/models"])
        self.assertEqual(Handler.seen[0][1], "Bearer test-only")

    def test_request_effort_and_tokens(self):
        result = core.translate(**self.args(reasoning_effort="high", token_parameter="max_completion_tokens"))
        self.assertEqual(result, "red dress, standing")
        path, auth, body = Handler.seen[-1]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertIn("max_completion_tokens", body)
        self.assertNotIn("temperature", body)
        self.assertIn("标签", body["messages"][0]["content"])
        self.assertNotIn("{target_language}", body["messages"][0]["content"])

    def test_auto_omits_reasoning_and_custom_prompt(self):
        core.translate(**self.args(mode="translate", system_prompt='Translate to {target_language}. JSON: {"a":1}', token_parameter="omit"))
        body = Handler.seen[-1][2]
        self.assertNotIn("reasoning_effort", body)
        self.assertNotIn("max_tokens", body)
        self.assertEqual(body["messages"][0]["content"], 'Translate to English. JSON: {"a":1}')

    def test_plain_translation_prompt(self):
        core.translate(**self.args(mode="translate"))
        self.assertIn("段落", Handler.seen[-1][2]["messages"][0]["content"])

    def test_chunk_lossless(self):
        text = ("第一句，有内容。第二句也有内容！\n\nAnother sentence. " * 30) + "尾巴"
        chunks = core.split_text(text, 100)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(c) <= 100 for c in chunks))
        self.assertEqual(core.split_text(text, 0), [text])

    def test_chunk_execution(self):
        text = "长段描述。" * 30
        core.translate(**self.args(text=text, chunk_chars=40))
        self.assertGreater(len(Handler.seen), 1)
        self.assertEqual("".join(x[2]["messages"][1]["content"] for x in Handler.seen), text)

    def test_empty_no_request(self):
        self.assertEqual(core.translate(**self.args(text=" \n")), "")
        self.assertEqual(Handler.seen, [])

    def test_response_errors(self):
        for data in ({}, {"choices": []}, {"choices": [{"finish_reason": "length"}]}, {"choices": [{"message": {"content": None}}]}, {"choices": [{"message": {"content": "<think>unfinished"}}]}):
            with self.assertRaises(core.APIError):
                core.extract_content(data)

    def test_content_array(self):
        self.assertEqual(core.extract_content({"choices": [{"message": {"content": [{"type": "text", "text": "译文"}]}}]}), "译文")

    def test_no_retry_on_auth_or_invalid_params(self):
        for status in (400, 401, 429, 500):
            with patch.object(core, "request_json", side_effect=core.APIError("error", status)) as mock:
                with self.assertRaises(core.APIError):
                    core.call_api(self.url, "", "chat", {})
                self.assertEqual(mock.call_count, 1)

    def test_protected_parameters(self):
        for extra in ('[]', '{"messages": []}', '{"reasoning_effort":"high"}', 'bad'):
            with self.assertRaises(ValueError):
                core.translate(**self.args(extra_body_json=extra))

    def test_environment_key(self):
        with patch.dict("os.environ", {"TRANSLATETAG_API_KEY": "env-key"}):
            self.assertEqual(core.resolve_key(""), "env-key")
            self.assertEqual(core.resolve_key("explicit"), "explicit")


if __name__ == "__main__":
    unittest.main()
