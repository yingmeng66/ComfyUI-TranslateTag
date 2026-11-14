import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "TranslateTag.Controls",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "TranslateTagText") return;
        const original = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = original?.apply(this, arguments);
            const widget = (name) => this.widgets.find((w) => w.name === name);
            const onConfigure = this.onConfigure;
            this.onConfigure = function () {
                onConfigure?.apply(this, arguments);
                const effort = widget("reasoning_effort");
                const legacy = { auto: "low", none: "不开启", minimal: "low" };
                if (effort && Object.hasOwn(legacy, effort.value)) effort.value = legacy[effort.value];
                const order = widget("prompt_order");
                if (order && ["角色优先", "服装优先", "背景优先"].includes(order.value)) order.value = "Anima 社区编排";
            };
            let loading = false;
            const selector = this.addWidget("combo", "选择模型", "请先刷新模型", (value) => {
                if (selector.options.values.includes(value) && value !== "请先刷新模型") widget("model").value = value;
            }, { values: ["请先刷新模型"], serialize: false });
            selector.serializeValue = () => undefined;
            this.addWidget("button", "刷新模型列表", null, async () => {
                if (loading) return;
                loading = true;
                const base = widget("base_url").value;
                const key = widget("api_key").value;
                selector.name = "正在获取模型…";
                try {
                    const response = await api.fetchApi("/translatetag/models", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ base_url: base, api_key: key }),
                    });
                    const data = await response.json();
                    if (!response.ok || data.error) throw new Error(data.error || `HTTP ${response.status}`);
                    if (widget("base_url").value !== base || widget("api_key").value !== key) return;
                    selector.options.values = data.models;
                    const current = widget("model").value;
                    selector.value = data.models.includes(current) ? current : data.models[0];
                    // Preserve manually configured models when the API list omits them.
                    if (!current) widget("model").value = selector.value;
                } catch (error) { alert(`TranslateTag：${error.message}`); }
                finally { loading = false; selector.name = "选择模型"; this.setDirtyCanvas(true, true); }
            }, { serialize: false });
            const testStatus = ComfyWidgets.STRING(this, "模型测试结果", ["STRING", { multiline: true }], app).widget;
            testStatus.options = { ...testStatus.options, serialize: false };
            testStatus.serializeValue = () => undefined;
            testStatus.value = "尚未测试。点击测试会发送一条简短文本，可能产生少量 API 费用。";
            if (testStatus.inputEl) testStatus.inputEl.readOnly = true;
            let testing = false;
            this.addWidget("button", "测试当前模型", null, async () => {
                if (testing) return;
                const names = ["base_url", "api_key", "model", "mode", "source_language", "target_language", "reasoning_effort", "system_prompt", "max_tokens", "token_parameter", "timeout", "extra_body_json", "prompt_order"];
                if (this.inputs?.some((input) => names.includes(input.name) && input.link != null)) {
                    testStatus.value = "测试按钮使用节点填写值；请先断开配置项的外部连接，或运行工作流验证连接值。";
                    this.setDirtyCanvas(true, true);
                    return;
                }
                const settings = Object.fromEntries(names.map((name) => [name, widget(name)?.value]));
                if (!settings.model?.trim()) {
                    testStatus.value = "请先选择模型或填写 model。";
                    this.setDirtyCanvas(true, true);
                    return;
                }
                testing = true;
                testStatus.value = `正在测试 ${settings.model}，最长等待约 ${settings.timeout} 秒…`;
                this.setDirtyCanvas(true, true);
                try {
                    const response = await api.fetchApi("/translatetag/test", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(settings),
                    });
                    if (response.status === 404) throw new Error("测试接口未加载，请重启 ComfyUI 并刷新网页。");
                    const data = await response.json();
                    if (!response.ok || data.error) throw new Error(data.error || `HTTP ${response.status}`);
                    const changed = names.some((name) => widget(name)?.value !== settings[name]);
                    testStatus.value = `${changed ? "参数已改变，以下为测试开始时的结果。\n" : ""}请求成功：${data.model}（${data.seconds} 秒）\n测试原文：一只白猫坐在窗边。\n模型返回：${data.text}\n已验证接口能返回文本；翻译质量及思考参数是否实际生效需按返回内容和服务文档判断。`;
                } catch (error) {
                    testStatus.value = `测试失败：${error.message}`;
                } finally {
                    testing = false;
                    this.setDirtyCanvas(true, true);
                }
            }, { serialize: false });
            this.addWidget("button", "载入当前模式默认系统提示词", null, async () => {
                try {
                    const response = await api.fetchApi("/translatetag/prompts");
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    const prompts = await response.json();
                    widget("system_prompt").value = prompts[widget("mode").value];
                    this.setDirtyCanvas(true, true);
                } catch (error) { alert(`TranslateTag：${error.message}`); }
            }, { serialize: false });
            const preview = ComfyWidgets.STRING(this, "翻译结果", ["STRING", { multiline: true }], app).widget;
            preview.options = { ...preview.options, serialize: false };
            preview.serializeValue = () => undefined;
            if (preview.inputEl) preview.inputEl.readOnly = true;
            const onExecuted = this.onExecuted;
            this.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                preview.value = message.text?.join("\n") || "";
                this.setDirtyCanvas(true, true);
            };
            this.setSize([480, Math.max(this.size[1], 740)]);
            return result;
        };
    },
});
