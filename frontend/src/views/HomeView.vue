<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="brand">
        <img
          v-show="logoSrc"
          src="/logo.png"
          alt=""
          class="logo-img"
          @error="logoSrc = false"
        />
        <span class="title">AI 小说助手</span>
      </div>
      <el-button type="primary" @click="settingsVisible = true">设置</el-button>
    </header>
    <div class="app-body">
      <aside class="left-panel">
        <LeftPanel />
      </aside>
      <main class="center-panel">
        <CenterPanel />
      </main>
      <aside class="right-panel">
        <RightPanel />
      </aside>
    </div>
    <SettingsModal v-model:visible="settingsVisible" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import LeftPanel from "@/components/LeftPanel/LeftPanel.vue";
import CenterPanel from "@/components/CenterPanel/CenterPanel.vue";
import RightPanel from "@/components/RightPanel/RightPanel.vue";
import SettingsModal from "@/components/Settings/SettingsModal.vue";
import { useNovelStore } from "@/stores/novel";
import { useSettingsStore } from "@/stores/settings";

const settingsVisible = ref(false);
const logoSrc = ref(true);
const store = useNovelStore();
const settingsStore = useSettingsStore();

onMounted(() => {
  store.fetchNovels();
  settingsStore.fetchSettings();
});
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color-page);
}
.app-header {
  height: 52px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-img {
  height: 28px;
  width: 28px;
  object-fit: contain;
  border-radius: 8px;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.app-body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.left-panel {
  width: 280px;
  border-right: 1px solid var(--el-border-color-lighter);
  overflow: auto;
  flex-shrink: 0;
  background: rgba(248, 249, 250, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.center-panel {
  flex: 1;
  min-width: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
.right-panel {
  width: 320px;
  border-left: 1px solid var(--el-border-color-lighter);
  overflow: auto;
  flex-shrink: 0;
  background: rgba(248, 249, 250, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
</style>
