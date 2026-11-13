import asyncio
import time
from aiohttp import web
from server import PromptServer
from .core import fetch_models, translate, TAG_PROMPT, TEXT_PROMPT, APIError


@PromptServer.instance.routes.post("/translatetag/models")
async def models(request):
    try:
        body = await request.json()
        if not isinstance(body, dict) or not isinstance(body.get("base_url"), str) or not isinstance(body.get("api_key", ""), str):
            raise ValueError("请填写有效的 URL 和 Key。")
        ids = await asyncio.to_thread(fetch_models, body["base_url"], body.get("api_key", ""))
        return web.json_response({"models": ids})
    except (ValueError, APIError) as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception:
        return web.json_response({"error": "模型获取失败，请检查服务配置。"}, status=500)


@PromptServer.instance.routes.get("/translatetag/prompts")
async def prompts(request):
    return web.json_response({"tags": TAG_PROMPT, "translate": TEXT_PROMPT})


@PromptServer.instance.routes.post("/translatetag/test")
async def test_model(request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("测试参数必须为 JSON 对象。")
        defaults = {
            "base_url": "", "api_key": "", "model": "", "mode": "tags",
            "source_language": "auto", "target_language": "English",
            "reasoning_effort": "low", "system_prompt": "",
            "token_parameter": "max_tokens", "extra_body_json": "{}",
        }
        args = {name: body.get(name, default) for name, default in defaults.items()}
        if any(not isinstance(value, str) for value in args.values()):
            raise ValueError("模型、接口和提示词参数必须为文本。")
        for name, default, minimum, maximum in (("max_tokens", 4096, 128, 131072), ("timeout", 120, 10, 1800)):
            value = body.get(name, default)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{name} 必须为 {minimum}–{maximum} 的整数。")
            args[name] = value
        started = time.monotonic()
        result = await asyncio.to_thread(
            translate, text="一只白猫坐在窗边。", chunk_chars=0, **args
        )
        return web.json_response({"model": args["model"], "seconds": round(time.monotonic() - started, 2), "text": result})
    except (ValueError, APIError) as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception:
        return web.json_response({"error": "模型测试失败，请检查服务配置。"}, status=500)
