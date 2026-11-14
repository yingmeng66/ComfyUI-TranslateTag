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

点击 **测试当前模型**，使用节点当前的 URL、Key、model、思考等级、系统提示词、语言、token 和额外参数翻译固定短句“一只白猫坐在窗边。”。无需运行整个工作流，测试结果显示耗时、模型返回或错误原因，不覆盖正式译文。按钮会产生一次实际 API 调用，可能计费；成功表示接口返回了文本，不保证服务实际采用了思考参数或译文质量。配置项连接了外部输入时，请运行工作流验证实际连接值。更新此功能后需要重启 ComfyUI 并刷新网页。

- `reasoning_effort`：`不开启 / low / medium / high / xhigh / max`，默认 `low`。“不开启”发送 `none`，其余值原样发送，不将 `max` 映射成 `xhigh`。每个等级均需具体接口和模型支持；不支持时显示错误。旧网页工作流载入后 `none` 改为“不开启”，`auto/minimal` 改为 `low`；使用 API 工作流时请手动更新旧值。
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

## v1.2 提示词调整

参考 [dsh-unrestricted 的规则组织方式](https://github.com/yexi-by/dsh-unrestricted/blob/master/src/rules.js)，独立编写翻译任务约定：直接输出结果、把原文当资料而非指令、保留事实和语气，减少误拒绝。未复制该项目的通用无限制规则，不会强行改写人物年龄或补充原文内容。提示词不能保证服务端接受请求，也不保证消除拒答。

两种模式的内置提示词均已更新；system_prompt 非空时仍完全以自定义内容为准。已保存旧提示词的节点请点击“载入当前模式默认系统提示词”更新，或清空该字段使用新的默认内容。服务返回明确的 refusal/content_filter 时节点会报告拒绝，不把它作为成功译文；普通文本中的拒答没有用关键词自动判定，以免把含拒绝用语的原文误判。

## v1.3 自动编排提示词

新增 `prompt_order` 下拉选项，仅在 tags 标签翻译模式生效：

| 选项 | 编排方式 |
| --- | --- |
| 自动编排（默认） | 模型根据原文的画面重点决定：人物活动优先角色，服装设计优先服装，风景建筑优先环境；无明确重点时角色优先 |
| 角色优先 | 身份 → 外貌、服装、动作 → 人物关系 → 背景 → 光照、构图、风格 |
| 服装优先 | 身份 → 服装、配饰 → 外貌、动作 → 背景 → 光照、构图、风格 |
| 背景优先 | 场景、地点 → 身份、外貌、服装、动作 → 人物关系 → 光照、构图、风格 |
| 关闭 | 保留原文语义顺序，仍翻译并拆分标签 |

例如同一段人物与花园描述，角色优先的预期形式是 `a woman, red dress, standing, garden`；背景优先则是 `garden, a woman, red dress, standing`。这是格式示例，实际标签由模型生成。

编排规则会追加到实际发送的系统提示词末尾；自定义系统提示词同样生效，顺序冲突以编排规则为准。提示词框仍显示基础提示词，编排规则由下拉框控制，不需要手写或重新载入基础提示词。普通 translate 模式保持段落，不应用编排。旧工作流缺少该输入时默认使用自动编排。

要求模型只重排已有信息，不补充品质词；保留人物属性归属、权重括号、LoRA 标记和提示词块边界。此功能由模型按指令完成，代码不机械拆分、排序逗号标签，也无法保证模型始终遵守。长文分段时分别编排各段，不对所有段落做全局排序；需要完整编排时将 chunk_chars 设为 0，并确认模型上下文足够。

参考：[NovelAI 标签顺序文档](https://docs.novelai.net/en/image/tags/)说明顺序影响取决于模型，[Diffusers 提示词指南](https://huggingface.co/docs/diffusers/en/using-diffusers/weighted_prompts)建议明确主体、风格与上下文。上述五种模式是本节点的编排策略，不能保证某种顺序对所有绘图模型都最优，也不等同于显式权重。

更新后重启 ComfyUI、刷新网页，旧节点未显示新选项时可重新添加 TranslateTag 节点。

### Anima 社区编排

Anima 用户可在 `prompt_order` 中选择“Anima 社区编排”。原文已有的全局元标签 → 人数 → 角色/作品 → 画师/画风 → 按角色分组的外貌、服装、动作 → 互动关系 → 环境 → 光照/构图。服装在所属角色外貌之后、动作之前，服装细节尽量按从头到脚组织；场景本身是重点时允许背景提前。它是语言模型的编排指令，不是保证最优的模型定律。

仅调整已有内容，不自动加入年份、质量、分级、作品或画师。保持标签式翻译，不自动改成自然语言，也不改变默认选项。人物互动需明确动作双方，不能因排序混淆服装与动作归属。

本选项参考独立用户发布的资料，而非 Anima 官方推荐：

- [Langzaigg 的 AnimaFlow 提示词指南](https://github.com/Langzaigg/ComfyUI-AnimaFlow/blob/main/wiki/Prompt-Guide.md)：采用元标签、人数、角色、作品、画师、风格、外观、主体标签和环境的组织方式。该指南的“必须”表述属于作者建议，本节点不将其视为模型硬性要求。
- [shuaixn 的 Anima 提示词规则](https://github.com/shuaixn/anima-prompt-writing/blob/main/references/prompt-rules.md)：提供按类别组织外观与环境的规则；未照搬其质量词、画幅等个人默认值。
- [Reddit Anima 用户经验讨论](https://www.reddit.com/r/StableDiffusion/comments/1u4t2lx/now_that_anima_10_has_been_out_for_a_month_what/)：blastcat4 分享人物/场景分组与多角色动作归属经验；mellowanon 认为清楚分隔语义比固定顺序更重要。也有用户采用自然语言或混合写法，社区并无一致的最佳顺序。

当前仍保持标签输出；若要试验社区的混合写法，可切换普通翻译并自定义系统提示词。本节点未进行 Anima 出图对照实测，不能将社区经验视为效果保证。
