<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NText, NIcon, NSpin } from 'naive-ui'
import { DocumentTextOutline, PricetagsOutline, NewspaperOutline, SettingsOutline, TrendingUpOutline } from '@vicons/ionicons5'
import PageHeader from '@/components/PageHeader.vue'
import * as papersApi from '@/api/papers'
import * as keywordsApi from '@/api/keywords'
import * as digestApi from '@/api/digest'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const stats = ref({
  totalPapers: 0,
  totalKeywords: 0,
  todayPapers: 0,
})

const quickLinks = [
  { label: '今日推荐', path: '/digest', icon: NewspaperOutline, color: '#6366f1', bg: '#eef2ff' },
  { label: '论文库', path: '/papers', icon: DocumentTextOutline, color: '#10b981', bg: '#ecfdf5' },
  { label: '关键词', path: '/keywords', icon: PricetagsOutline, color: '#f59e0b', bg: '#fffbeb' },
  { label: '设置', path: '/settings', icon: SettingsOutline, color: '#8b5cf6', bg: '#f5f3ff' },
]

onMounted(async () => {
  try {
    const [papersRes, keywordsRes] = await Promise.all([
      papersApi.listPapers({ page: 1, size: 1 }),
      keywordsApi.listKeywords(),
    ])
    stats.value.totalPapers = papersRes.data.total
    stats.value.totalKeywords = keywordsRes.data.total

    try {
      const digestRes = await digestApi.getTodayDigest()
      stats.value.todayPapers = digestRes.data.papers.length
    } catch {
      // no digest today
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader :title="`欢迎回来，${auth.user?.username || ''}`" description="这是你的论文推荐系统概览" />

    <div v-if="loading" class="loading-state">
      <NSpin size="large" />
    </div>

    <template v-else>
      <div class="stats-grid">
        <NCard class="stat-card" :bordered="true">
          <div class="stat-icon" style="background: #eef2ff; color: #6366f1;">
            <NIcon :size="24"><NewspaperOutline /></NIcon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.todayPapers }}</span>
            <span class="stat-label">今日推荐</span>
          </div>
        </NCard>

        <NCard class="stat-card" :bordered="true">
          <div class="stat-icon" style="background: #ecfdf5; color: #10b981;">
            <NIcon :size="24"><DocumentTextOutline /></NIcon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.totalPapers }}</span>
            <span class="stat-label">论文总数</span>
          </div>
        </NCard>

        <NCard class="stat-card" :bordered="true">
          <div class="stat-icon" style="background: #fffbeb; color: #f59e0b;">
            <NIcon :size="24"><PricetagsOutline /></NIcon>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.totalKeywords }}</span>
            <span class="stat-label">关键词数</span>
          </div>
        </NCard>
      </div>

      <h3 class="section-title">快捷入口</h3>
      <div class="quick-grid">
        <NCard
          v-for="link in quickLinks"
          :key="link.path"
          class="quick-card"
          :bordered="true"
          hoverable
          @click="router.push(link.path)"
        >
          <div class="quick-icon" :style="{ background: link.bg, color: link.color }">
            <NIcon :size="28"><component :is="link.icon" /></NIcon>
          </div>
          <span class="quick-label">{{ link.label }}</span>
        </NCard>
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading-state {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 36px;
}

.stat-card {
  border-radius: 16px !important;
  border: 1px solid #f0f0f0 !important;
}

.stat-card :deep(.n-card__content) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px !important;
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: #111827;
  line-height: 1.1;
  letter-spacing: -0.5px;
}

.stat-label {
  font-size: 13px;
  color: #9ca3af;
  margin-top: 4px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 16px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.quick-card {
  border-radius: 16px !important;
  cursor: pointer;
  text-align: center;
  border: 1px solid #f0f0f0 !important;
  transition: all 0.2s ease;
}

.quick-card:hover {
  border-color: #e0e7ff !important;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08) !important;
  transform: translateY(-2px);
}

.quick-card :deep(.n-card__content) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 28px 20px !important;
}

.quick-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.quick-label {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .quick-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
