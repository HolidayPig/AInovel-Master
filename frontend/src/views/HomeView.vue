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
      <el-button type="primary" class="header-settings" @click="settingsVisible = true">
        <el-icon><Setting /></el-icon>
        Settings
      </el-button>
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
    <GlobalAiProgress />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Setting } from "@element-plus/icons-vue";
import LeftPanel from "@/components/LeftPanel/LeftPanel.vue";
import CenterPanel from "@/components/CenterPanel/CenterPanel.vue";
import RightPanel from "@/components/RightPanel/RightPanel.vue";
import SettingsModal from "@/components/Settings/SettingsModal.vue";
import GlobalAiProgress from "@/components/common/GlobalAiProgress.vue";
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
  background: linear-gradient(160deg, var(--el-bg-color-page) 0%, var(--el-fill-color-light) 100%);
}
.app-header {
  height: 52px;
  padding: 0 20px;
  margin: 10px 12px 0;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.38);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
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
.header-settings {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px !important;
  border-radius: 999px !important;
}
.app-body {
  flex: 1;
  display: flex;
  gap: 12px;
  padding: 12px;
  min-height: 0;
}
.left-panel {
  width: 280px;
  border-radius: 16px;
  overflow: hidden;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.52);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.75);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.25s ease, border-color 0.25s ease;
}
.left-panel:hover {
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.08);
}
.center-panel {
  flex: 1;
  min-width: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 4px 28px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.25s ease;
}
.right-panel {
  width: 320px;
  border-radius: 16px;
  overflow: hidden;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.52);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.75);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.25s ease, border-color 0.25s ease;
}
.right-panel:hover {
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.08);
}
</style>
