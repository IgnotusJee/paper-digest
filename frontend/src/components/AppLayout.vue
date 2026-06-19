<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NLayout, NLayoutSider, NLayoutHeader, NLayoutContent, NMenu, NButton, NIcon, NText, NAvatar, NDropdown } from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  NewspaperOutline,
  AlbumsOutline,
  DocumentTextOutline,
  PricetagsOutline,
  SettingsOutline,
  LogOutOutline,
  PersonOutline,
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)

const menuOptions: MenuOption[] = [
  { label: '今日推荐', key: '/digest', icon: () => h(NIcon, null, { default: () => h(NewspaperOutline) }) },
  { label: '论文库', key: '/papers', icon: () => h(NIcon, null, { default: () => h(DocumentTextOutline) }) },
  { label: '关键词', key: '/keywords', icon: () => h(NIcon, null, { default: () => h(PricetagsOutline) }) },
  { label: '设置', key: '/settings', icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }) },
]

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/papers/')) return '/papers'
  return path
})

const currentTitle = computed(() => {
  return menuOptions.find(m => m.key === activeKey.value)?.label || 'Paper Digest'
})

function handleMenuUpdate(key: string) {
  router.push(key)
}

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

const userDropdownOptions = [
  { label: '退出登录', key: 'logout', icon: () => h(NIcon, null, { default: () => h(LogOutOutline) }) },
]

function handleUserDropdown(key: string) {
  if (key === 'logout') handleLogout()
}
</script>

<template>
  <NLayout has-sider style="height: 100vh">
    <NLayoutSider
      bordered
      :collapsed="collapsed"
      collapse-mode="width"
      :collapsed-width="72"
      :width="240"
      show-trigger="bar"
      @collapse="collapsed = true"
      @expand="collapsed = false"
      :native-scrollbar="false"
      class="app-sider"
    >
      <div class="logo" :class="{ collapsed }">
        <div class="logo-icon">
          <NIcon :size="collapsed ? 24 : 22" color="#fff"><AlbumsOutline /></NIcon>
        </div>
        <transition name="fade">
          <span v-if="!collapsed" class="logo-text">Paper Digest</span>
        </transition>
      </div>

      <div class="sider-menu">
        <NMenu
          :collapsed="collapsed"
          :collapsed-width="72"
          :collapsed-icon-size="22"
          :options="menuOptions"
          :value="activeKey"
          @update:value="handleMenuUpdate"
          :theme-overrides="{
            itemTextColor: '#94a3b8',
            itemTextColorHover: '#e2e8f0',
            itemTextColorActive: '#ffffff',
            itemColorActive: 'rgba(99, 102, 241, 0.2)',
            itemColorHover: 'rgba(255, 255, 255, 0.04)',
            itemIconColor: '#64748b',
            itemIconColorHover: '#e2e8f0',
            itemIconColorActive: '#a5b4fc',
            borderRadius: '10px',
          }"
        />
      </div>

      <div class="sider-footer" :class="{ collapsed }">
        <div class="sider-user">
          <div class="user-avatar">
            <NIcon :size="18" color="#a5b4fc"><PersonOutline /></NIcon>
          </div>
          <transition name="fade">
            <div v-if="!collapsed" class="user-info">
              <span class="user-name">{{ auth.user?.username }}</span>
              <span class="user-role">管理员</span>
            </div>
          </transition>
        </div>
      </div>
    </NLayoutSider>

    <NLayout>
      <NLayoutHeader class="app-header">
        <div class="header-left">
          <h1 class="header-title">{{ currentTitle }}</h1>
        </div>
        <div class="header-right">
          <NButton quaternary circle size="small" @click="handleLogout" title="退出登录">
            <template #icon><NIcon :size="18"><LogOutOutline /></NIcon></template>
          </NButton>
        </div>
      </NLayoutHeader>

      <NLayoutContent
        :native-scrollbar="false"
        class="app-content"
        content-style="min-height: calc(100vh - 64px);"
      >
        <div class="content-wrapper">
          <RouterView />
        </div>
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>

<style scoped>
.app-sider {
  background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 20px;
  transition: all 0.3s ease;
}

.logo.collapsed {
  justify-content: center;
  padding: 24px 0 20px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #f1f5f9;
  white-space: nowrap;
  letter-spacing: -0.3px;
}

.sider-menu {
  padding: 8px 12px;
  flex: 1;
}

.sider-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: auto;
}

.sider-footer.collapsed {
  padding: 16px 8px;
}

.sider-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  transition: all 0.3s ease;
}

.sider-footer.collapsed .sider-user {
  justify-content: center;
  padding: 10px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  line-height: 1.2;
}

.user-role {
  font-size: 11px;
  color: #64748b;
  line-height: 1.2;
  margin-top: 2px;
}

.app-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #f0f0f0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  margin: 0;
  letter-spacing: -0.3px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-content {
  background: #f8fafc !important;
}

.content-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px 32px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .content-wrapper {
    padding: 16px;
  }

  .app-header {
    padding: 0 16px;
  }
}
</style>
