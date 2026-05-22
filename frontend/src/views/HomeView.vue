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
      <div class="header-actions">
        <el-button class="layout-toggle" :type="leftCollapsed ? 'primary' : 'default'" @click="toggleLeft">
          <el-icon><Fold /></el-icon>
          左栏
        </el-button>
        <el-button class="layout-toggle" :type="rightCollapsed ? 'primary' : 'default'" @click="toggleRight">
          <el-icon><Fold /></el-icon>
          右栏
        </el-button>
        <el-button type="primary" class="header-settings" @click="settingsVisible = true">
          <el-icon><Setting /></el-icon>
          Settings
        </el-button>
      </div>
    </header>
    <div class="app-body">
      <aside v-if="leftCollapsed" class="collapsed-rail" title="展开左栏" @click="toggleLeft">
        <el-icon><Menu /></el-icon>
        <span>导航</span>
      </aside>
      <aside v-else class="left-panel">
        <LeftPanel />
      </aside>
      <main class="center-panel">
        <WorkspaceView v-if="store.centerMode === 'workspace'" />
        <CenterPanel v-else />
      </main>
      <aside v-if="rightCollapsed" class="collapsed-rail collapsed-rail--right" title="展开右栏" @click="toggleRight">
        <el-icon><Collection /></el-icon>
        <span>卡片</span>
      </aside>
      <aside v-else class="right-panel">
        <RightPanel />
      </aside>
    </div>
    <SettingsModal v-model:visible="settingsVisible" />
    <GlobalAiProgress />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { Collection, Fold, Menu, Setting } from "@element-plus/icons-vue";
import LeftPanel from "@/components/LeftPanel/LeftPanel.vue";
import CenterPanel from "@/components/CenterPanel/CenterPanel.vue";
import WorkspaceView from "@/views/WorkspaceView.vue";
import RightPanel from "@/components/RightPanel/RightPanel.vue";
import SettingsModal from "@/components/Settings/SettingsModal.vue";
import GlobalAiProgress from "@/components/common/GlobalAiProgress.vue";
import { useNovelStore } from "@/stores/novel";
import { useSettingsStore } from "@/stores/settings";

const settingsVisible = ref(false);
const logoSrc = ref(true);
const store = useNovelStore();
const settingsStore = useSettingsStore();
const leftCollapsed = ref(localStorage.getItem("ainovel.leftCollapsed") === "1");
const rightCollapsed = ref(localStorage.getItem("ainovel.rightCollapsed") === "1");

onMounted(() => {
  store.fetchNovels();
  settingsStore.fetchSettings();
});

watch(leftCollapsed, (v) => localStorage.setItem("ainovel.leftCollapsed", v ? "1" : "0"));
watch(rightCollapsed, (v) => localStorage.setItem("ainovel.rightCollapsed", v ? "1" : "0"));

function toggleLeft() {
  leftCollapsed.value = !leftCollapsed.value;
}

function toggleRight() {
  rightCollapsed.value = !rightCollapsed.value;
}
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
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-settings,
.layout-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px !important;
  border-radius: 999px !important;
}
.layout-toggle {
  padding: 0 14px !important;
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
.collapsed-rail {
  width: 48px;
  border-radius: 16px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  color: var(--el-text-color-secondary);
  background: rgba(255, 255, 255, 0.52);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.75);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  transition: color 0.2s ease, box-shadow 0.2s ease;
}
.collapsed-rail:hover {
  color: var(--el-color-primary);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.08);
}
.collapsed-rail span {
  writing-mode: vertical-rl;
  font-size: 12px;
  letter-spacing: 0.1em;
}
</style>
