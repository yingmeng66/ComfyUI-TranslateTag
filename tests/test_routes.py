import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from aiohttp import web

root = Path(__file__).parents[1]
server_stub = types.ModuleType("server")
server_stub.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=web.RouteTableDef()))
spec = importlib.util.spec_from_file_location("translatetag_route_test", root / "__init__.py", submodule_search_locations=[str(root)])
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
with patch.dict(sys.modules, {"server": server_stub}):
    spec.loader.exec_module(package)
routes = package.routes


class Request:
    def __init__(self, body):
        self.body = body

    async def json(self):
        return self.body


class ModelTestRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_uses_current_settings_and_fixed_sample(self):
        params = {"base_url": "https://example.invalid/v1", "model": "chosen-model", "api_key": "fake", "reasoning_effort": "high", "max_tokens": 8192, "token_parameter": "max_completion_tokens", "system_prompt": "My prompt", "prompt_order": "服装优先"}
        with patch.object(routes, "translate", return_value="white cat") as translate:
            response = await routes.test_model(Request(params))
        self.assertEqual(response.status, 200)
        result = json.loads(response.text)
        self.assertEqual(result["text"], "white cat")
        self.assertEqual(result["model"], "chosen-model")
        for name, value in params.items():
            self.assertEqual(translate.call_args.kwargs[name], value)
        self.assertEqual(translate.call_args.kwargs["text"], "一只白猫坐在窗边。")

    async def test_api_failure(self):
        with patch.object(routes, "translate", side_effect=routes.APIError("HTTP 401", 401)):
            response = await routes.test_model(Request({"model": "x"}))
        self.assertEqual(response.status, 400)
        self.assertIn("401", json.loads(response.text)["error"])

    async def test_invalid_input_does_not_call_service(self):
        for params in ([], {"model": []}, {"timeout": "bad"}, {"max_tokens": -1}):
            with patch.object(routes, "translate") as translate:
                response = await routes.test_model(Request(params))
                self.assertEqual(response.status, 400)
                translate.assert_not_called()

    async def test_unexpected_error_does_not_leak_details(self):
        with patch.object(routes, "translate", side_effect=RuntimeError("secret")):
            response = await routes.test_model(Request({"model": "x"}))
        self.assertEqual(response.status, 500)
        self.assertNotIn("secret", response.text)
