import asyncio
from aiohttp import web
from server import PromptServer
from .core import fetch_models, TAG_PROMPT, TEXT_PROMPT, APIError


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
