from .core import EFFORTS, PROMPT_ORDERS, translate

LANGUAGES = ["auto", "English", "简体中文", "繁體中文", "日本語", "한국어", "Deutsch", "Français", "Español", "Русский"]


class TranslateTag:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "text": ("STRING", {"multiline": True, "default": ""}),
            "base_url": ("STRING", {"default": "https://api.openai.com", "tooltip": "支持域名、/v1、完整 /chat/completions 或自定义 API 前缀"}),
            "api_key": ("STRING", {"default": "", "tooltip": "留空使用 TRANSLATETAG_API_KEY 或 config.json；填写后会随工作流保存"}),
            "model": ("STRING", {"default": "", "tooltip": "刷新模型后选择，或手动填写模型 ID"}),
            "mode": (["tags", "translate"], {"default": "tags", "tooltip": "tags：标签式翻译；translate：普通翻译"}),
            "source_language": (LANGUAGES, {"default": "auto"}),
            "target_language": (LANGUAGES[1:], {"default": "English"}),
            "reasoning_effort": (EFFORTS, {"default": "low", "tooltip": "不开启发送 none；low/medium/high/xhigh/max 原样发送，各等级需接口支持"}),
            "system_prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "留空使用对应模式内置提示词；点击下方按钮可载入修改。支持 {source_language} 和 {target_language}"}),
            "chunk_chars": ("INT", {"default": 6000, "min": 0, "max": 200000, "step": 500, "tooltip": "按段落/句子分段的字符上限，0 禁用；跨段上下文不共享"}),
            "max_tokens": ("INT", {"default": 4096, "min": 128, "max": 131072}),
            "token_parameter": (["max_tokens", "max_completion_tokens", "omit"], {"default": "max_tokens"}),
            "timeout": ("INT", {"default": 120, "min": 10, "max": 1800}),
            "extra_body_json": ("STRING", {"default": "{}", "multiline": True, "tooltip": "服务商额外参数，如 temperature、chat_template_kwargs；原样发送"}),
            "refresh_seed": ("INT", {"default": 0, "min": 0, "max": 2147483647, "tooltip": "相同输入由 ComfyUI 缓存；更改此值重新请求"}),
        }, "optional": {
            "prompt_order": (list(PROMPT_ORDERS), {"default": "Anima 社区编排", "tooltip": "仅标签模式生效。Anima 社区编排：按角色组织外貌、服装、动作，明确互动关系；自动编排：通用画面重点判断；关闭：保留原文顺序。规则追加到系统提示词末尾。"}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_text",)
    FUNCTION = "execute"
    CATEGORY = "TranslateTag"
    OUTPUT_NODE = True

    def execute(self, refresh_seed=0, **kwargs):
        result = translate(**kwargs)
        return {"ui": {"text": [result]}, "result": (result,)}
