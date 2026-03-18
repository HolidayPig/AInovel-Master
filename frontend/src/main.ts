import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import { ElMessage } from "element-plus";
import "element-plus/dist/index.css";
import "@/styles/ios-theme.css";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);
app.use(ElementPlus);

/** 部署初期：错误提示不自动消失，需用户点 × 关闭，便于复制与排查 */
{
  (ElMessage as { error: (p: string | Record<string, unknown>) => ReturnType<typeof ElMessage> }).error = (
    msgOrOpts: string | Record<string, unknown>
  ) => {
    if (typeof msgOrOpts === "string" || typeof msgOrOpts === "number") {
      return ElMessage({ type: "error", message: String(msgOrOpts), duration: 0, showClose: true });
    }
    const o = (msgOrOpts || {}) as Record<string, unknown>;
    return ElMessage({
      ...o,
      type: "error",
      message: typeof o.message === "string" ? o.message : String(o.message ?? ""),
      duration: 0,
      showClose: true,
    });
  };
}

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}
app.mount("#app");
