import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let extension;
let reply = { models: ["model-a", "model-b"] };
let lastRequest;
const alerts = [];
const app = { registerExtension(value) { extension = value; } };
const api = { async fetchApi(path, options) {
    lastRequest = { path, options };
    return { ok: true, async json() { return reply; } };
} };
const ComfyWidgets = { STRING(node, name) {
    const widget = node.addWidget("text", name, "", () => {}, {});
    widget.inputEl = {};
    return { widget };
} };
const source = fs.readFileSync(new URL("../js/translatetag.js", import.meta.url), "utf8").replace(/^import .*;\r?\n/gm, "");
vm.runInNewContext(source, { app, api, ComfyWidgets, alert(value) { alerts.push(value); } });
class Node {
    constructor() {
        this.widgets = [];
        this.size = [100, 100];
        for (const [name, value] of Object.entries({ base_url: "https://test.invalid/v1", api_key: "fake-key", model: "", mode: "tags", system_prompt: "" })) {
            this.addWidget("text", name, value, () => {}, {});
        }
    }
    addWidget(type, name, value, callback, options) {
        const widget = { type, name, value, callback, options };
        this.widgets.push(widget);
        return widget;
    }
    setSize(size) { this.size = size; }
    setDirtyCanvas() {}
}
await extension.beforeRegisterNodeDef(Node, { name: "TranslateTagText" });
const node = new Node();
node.onNodeCreated();
const w = (name) => node.widgets.find((widget) => widget.name === name);
await w("刷新模型列表").callback();
assert.equal(w("model").value, "model-a");
assert.equal(lastRequest.path, "/translatetag/models");
assert.equal(JSON.parse(lastRequest.options.body).api_key, "fake-key");
w("选择模型").callback("model-b");
assert.equal(w("model").value, "model-b");
w("model").value = "manual-model";
await w("刷新模型列表").callback();
assert.equal(w("model").value, "manual-model");
reply = { tags: "tag prompt", translate: "translation prompt" };
await w("载入当前模式默认系统提示词").callback();
assert.equal(w("system_prompt").value, "tag prompt");
w("mode").value = "translate";
await w("载入当前模式默认系统提示词").callback();
assert.equal(w("system_prompt").value, "translation prompt");
node.onExecuted({ text: ["translated output"] });
assert.equal(w("翻译结果").value, "translated output");
assert.equal(w("翻译结果").inputEl.readOnly, true);
assert.equal(w("翻译结果").serializeValue(), undefined);
reply = { error: "Test error" };
await w("刷新模型列表").callback();
assert.equal(alerts.length, 1);
assert.equal(w("选择模型").name, "选择模型");
reply = { model: "manual-model", seconds: 1.2, text: "white cat, sitting by a window" };
await w("测试当前模型").callback();
assert.equal(lastRequest.path, "/translatetag/test");
assert.equal(JSON.parse(lastRequest.options.body).model, "manual-model");
assert.match(w("模型测试结果").value, /请求成功/);
assert.match(w("模型测试结果").value, /white cat/);
reply = { error: "接口 HTTP 401。检查 API Key。" };
await w("测试当前模型").callback();
assert.match(w("模型测试结果").value, /测试失败.*401/);
w("model").value = "";
await w("测试当前模型").callback();
assert.match(w("模型测试结果").value, /请先选择模型/);
assert.equal(w("模型测试结果").serializeValue(), undefined);
node.addWidget("text", "reasoning_effort", "none", () => {}, {});
node.onConfigure();
assert.equal(w("reasoning_effort").value, "不开启");
w("reasoning_effort").value = "auto";
node.onConfigure();
assert.equal(w("reasoning_effort").value, "low");
w("reasoning_effort").value = "max";
node.onConfigure();
assert.equal(w("reasoning_effort").value, "max");
console.log("Frontend controls passed: model refresh/selection, manual model preservation, prompt loading, preview, error handling.");
