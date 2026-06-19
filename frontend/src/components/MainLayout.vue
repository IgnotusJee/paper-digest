<template>
  <n-layout has-sider position="absolute" style="height: 100vh;">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      style="background-color: #0f172a;"
    >
      <div class="logo-area" :class="{ collapsed }">
        <span class="logo-icon">📚</span>
        <span v-if="!collapsed" class="logo-text">Paper Digest</span>
      </div>
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        inverted
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>
    <n-layout>
      <n-layout-header bordered style="height: 64px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between;">
        <div style="font-weight: 500; font-size: 16px;">
          {{ currentRouteTitle }}
        </div>
        <div v-if="user" style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 14px; color: #4b5563;">{{ user.username }} ({{ user.email }})</span>
          <n-button size="small" secondary type="error" @click="handleLogout">
            退出登录
          </n-button>
        </div>
      </n-layout-header>
      <n-layout-content content-style="padding: 24px;" style="background-color: #f8fafc; height: calc(100vh - 64px); overflow-y: auto;">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useMessage } from 'naive-ui';

// Simple Emoji placeholders for icons
const renderIcon = (emoji: string) => {
  return () => h('span', { style: 'font-size: 18px;' }, emoji);
};

const collapsed = ref(false);
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const message = useMessage();

const user = computed(() => authStore.user);

const activeKey = computed(() => {
  const name = route.name as string;
  return name ? name.toLowerCase() : 'digest';
});

const currentRouteTitle = computed(() => {
  switch (route.name) {
    case 'Dashboard': return '数据看板';
    case 'Digest': return '今日推荐';
    case 'Papers': return '论文总览';
    case 'PaperDetail': return '论文详情';
    case 'Keywords': return '关键词管理';
    case 'Settings': return '系统设置';
    default: return 'AI 论文日报';
  }
});

const menuOptions = [
  {
    label: '今日推荐',
    key: 'digest',
    icon: renderIcon('✨')
  },
  {
    label: '数据看板',
    key: 'dashboard',
    icon: renderIcon('📊')
  },
  {
    label: '论文总览',
    key: 'papers',
    icon: renderIcon('📄')
  },
  {
    label: '关键词管理',
    key: 'keywords',
    icon: renderIcon('🔑')
  },
  {
    label: '系统设置',
    key: 'settings',
    icon: renderIcon('⚙️')
  }
];

function handleMenuSelect(key: string) {
  if (key === 'digest') router.push('/digest');
  else if (key === 'dashboard') router.push('/dashboard');
  else if (key === 'papers') router.push('/papers');
  else if (key === 'keywords') router.push('/keywords');
  else if (key === 'settings') router.push('/settings');
}

async function handleLogout() {
  try {
    await authStore.logout();
    message.success('已安全退出');
    router.push('/login');
  } catch (err) {
    message.error('退出失败');
  }
}
</script>

<style scoped>
.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.logo-area.collapsed {
  justify-content: center;
  padding: 0;
}
.logo-icon {
  font-size: 24px;
}
.logo-text {
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}
</style>
