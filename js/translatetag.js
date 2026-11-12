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
