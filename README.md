# ComfyUI-TranslateTag

面向 OpenAI-compatible Chat Completions 接口的翻译节点。参考 TranslateLink 的单节点使用方式，独立实现，不依赖原插件。

## 安装

将整个 `ComfyUI-TranslateTag` 文件夹放入 `ComfyUI/custom_nodes/`，重启 ComfyUI 并刷新网页。
搜索 **TranslateTag**，添加 **TranslateTag · Translate Text / 标签翻译**。
无需 pip 安装；网络调用使用 Python 标准库，路由使用 ComfyUI 自带的 aiohttp。需要 Python 3.9+。

## 使用

1. 填入 `base_url` 和 `api_key`。
2. 点击 **刷新模型列表**，在 **选择模型** 下拉框中选择模型。`model` 是实际执行使用的模型 ID，也可直接手动填写；服务未实现 `/models` 时仍可执行翻译。
3. 填写或连接 `text`，选择源语言（默认自动识别）和目标语言（默认英文）。
4. 选择模式，按需设置思考等级，运行工作流。
5. `translated_text` 输出连接 CLIP Text Encode 的文本输入，或其他 STRING 输入；节点下方同时预览结果。

### 两种翻译模式

- **tags（默认）**：将原文翻译成目标语言的绘图标签；长段落按语义拆成短语，以英文逗号分隔，保留人物属性归属、数量、动作、否定关系、场景和构图。默认提示词明确禁止普通长句、解释、凭空添加品质词。
- **translate**：普通翻译，保留原文语气和段落。

例如原文“一个穿红裙的女孩站在雨夜街道上，身后是霓虹灯，镜头从侧面拍摄”，标签式翻译的预期形式为：
`a girl, red dress, standing on a street, rainy night, neon lights in background, side view`
这是格式示例，实际措辞取决于模型。

### 系统提示词

`system_prompt` 留空会随模式自动使用对应内置提示词。点击 **载入当前模式默认系统提示词** 可以查看并编辑完整内容（会替换当前文本）。
非空时以你的自定义提示词为准，切换模式不会覆盖已填写的提示词；清空即可恢复模式默认。
支持 `{source_language}`、`{target_language}` 占位符，其他花括号（例如 JSON 示例）保持原样。
标签拆解由语言模型完成，插件不把普通译文机械切词；模型是否严格遵守格式取决于其指令遵循能力。

### URL 自动补全

| 填写内容 | 优先请求的聊天接口 |
| --- | --- |
| `https://host` 或 `host` | `https://host/v1/chat/completions` |
| `https://host/v1` | `https://host/v1/chat/completions` |
| `https://host/api/v1` | `https://host/api/v1/chat/completions` |
| `https://host/custom` | `https://host/custom/chat/completions` |
| 完整 `/chat/completions` 地址 | 保持路径不变 |
| 完整 `/models` 地址 | 将末尾替换为 `/chat/completions` |

模型列表使用相同前缀下的 `/models`。根域名 `/v1` 路径返回 404 时尝试无版本路径；自定义前缀返回 404 时尝试加 `/v1`。401/400 等错误不换地址、不静默删参数。服务返回其他状态时请直接填写其完整接口地址。
省略协议时默认 HTTPS；localhost、127.0.0.1 和 [::1] 默认 HTTP。其他局域网地址请明确填写 `http://`。
支持 Chat Completions 兼容服务，不包含 Google/百度独立翻译协议、原生 Ollama `/api/chat` 或仅支持 Responses 的接口。

### 思考等级与兼容参数

- `reasoning_effort`：`auto / none / minimal / low / medium / high / xhigh`。`auto` 不发送该参数，使用服务默认；**不等于关闭思考**。其他值原样发送，是否支持由具体模型和服务决定，不支持时会显示错误。
- `token_parameter`：老兼容服务用 `max_tokens`；需要新字段的推理模型用 `max_completion_tokens`；`omit` 不传上限。
- `max_tokens`：每段请求的输出额度。部分推理模型会把思考 token 也计入，出现截断时调大。插件遇到 `finish_reason=length` 会报错，不把残缺译文当成功。
- `extra_body_json`：服务商专属参数对象，例如 `{"temperature":0.2}` 或服务明确支持的 `{"chat_template_kwargs":{"enable_thinking":false}}`。默认不传 temperature，减少与推理模型的冲突。禁止覆盖消息、模型、思考等级和 token 参数。
- `timeout`：每次请求超时秒数，默认 120；慢推理模型可以调大。
- `refresh_seed`：相同输入可能被 ComfyUI 缓存；修改此值可重新翻译。

### 长文

`chunk_chars` 默认 6000 字符，优先在段落、句子、空白处切分，找不到合适边界才按长度切分；0 表示不分段。
每段单独翻译，普通模式按段落连接，默认标签模式按逗号连接。不会丢弃输入字符，也不会自动删除重复语义。
分段调用不共享跨段上下文。多人物关系复杂或依赖上下文的文本，可提高分段上限或禁用分段，并确认模型上下文足够。字符上限不是 token 上限。
任何一段失败都会报错，不输出假装完整的部分译文；再次执行会重新请求各段。网络错误不会自动重试，以免超时后重复计费。

### Key 配置

优先级：节点 `api_key` > `TRANSLATETAG_API_KEY` 环境变量 > 插件目录 `config.json` 的 `api_key`。
可将 `config.example.json` 复制为 `config.json` 填写密钥，模型刷新和翻译共用配置。本地免鉴权服务可全部留空。
节点填写的 Key 会进入工作流文件，分享前清空；使用环境变量或 config.json 可避免把 Key 放进工作流。不要分享 config.json。
HTTP 错误仅显示状态和排错建议，不回显服务响应、Key 或用户原文。TLS 证书验证保持开启，不跟随重定向传递 Key。

## 验证

`python -m unittest discover -s tests -v`

测试使用本地模拟 HTTP 服务验证 URL 补全、模型列表、鉴权、请求参数、分段和异常，不需要真实 API Key。
前端控件回归测试：`node tests/test_frontend.mjs`。

## 参考文档

- [TranslateLink 中文说明](https://github.com/leafiy/ComfyUI-TranslateLink/blob/main/README.zh-CN.md)
- [OpenAI Chat Completions 参数](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [ComfyUI 节点属性](https://docs.comfy.org/custom-nodes/backend/server_overview)
- [ComfyUI JavaScript 扩展](https://docs.comfy.org/custom-nodes/js/javascript_overview)
