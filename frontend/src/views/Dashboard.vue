<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NIcon, NSpin, NTag } from 'naive-ui'
import {
  DocumentTextOutline,
  PricetagsOutline,
  NewspaperOutline,
  SettingsOutline,
  SparklesOutline,
  GitNetworkOutline,
} from '@vicons/ionicons5'
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
  { label: '今日推荐', path: '/digest', icon: NewspaperOutline, meta: '查看当天 digest' },
  { label: '论文库', path: '/papers', icon: DocumentTextOutline, meta: '检索历史论文' },
  { label: '关键词', path: '/keywords', icon: PricetagsOutline, meta: '维护订阅主题' },
  { label: '设置', path: '/settings', icon: SettingsOutline, meta: '调节推送策略' },
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
    <PageHeader
      :title="`欢迎回来，${auth.user?.username || ''}`"
      description="你的研究阅读工作台。先看今日推荐，再决定追踪哪些主题和来源。"
    />

    <div v-if="loading" class="loading-state">
      <NSpin size="large" />
    </div>

    <template v-else>
      <div class="overview-grid">
        <NCard class="hero-card" :bordered="false">
          <div class="hero-eyebrow">
            <span class="eyebrow-dot"></span>
            Research brief
          </div>
          <h2 class="hero-title">今天有 {{ stats.todayPapers }} 篇值得先读的论文。</h2>
          <p class="hero-copy">系统会按 venue 与 arXiv 分桶推送，适合先扫读、再进入细看。</p>
          <div class="hero-tags">
            <NTag round :bordered="false" class="hero-tag">
              <template #icon><NIcon :component="SparklesOutline" /></template>
              每日精选
            </NTag>
            <NTag round :bordered="false" class="hero-tag">
              <template #icon><NIcon :component="GitNetworkOutline" /></template>
              关键词订阅
            </NTag>
          </div>
          <div class="hero-inline-stats">
            <div class="inline-stat">
              <span class="inline-value">{{ stats.totalPapers }}</span>
              <span class="inline-label">累计论文</span>
            </div>
            <div class="inline-stat">
              <span class="inline-value">{{ stats.totalKeywords }}</span>
              <span class="inline-label">追踪主题</span>
            </div>
          </div>
        </NCard>

        <div class="stats-stack">
          <NCard class="stat-card" :bordered="false">
            <div class="stat-icon">
              <NIcon :size="22"><NewspaperOutline /></NIcon>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ stats.todayPapers }}</span>
              <span class="stat-label">今日推荐</span>
            </div>
          </NCard>
          <NCard class="stat-card" :bordered="false">
            <div class="stat-icon">
              <NIcon :size="22"><DocumentTextOutline /></NIcon>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ stats.totalPapers }}</span>
              <span class="stat-label">论文总数</span>
            </div>
          </NCard>
          <NCard class="stat-card" :bordered="false">
            <div class="stat-icon">
              <NIcon :size="22"><PricetagsOutline /></NIcon>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ stats.totalKeywords }}</span>
              <span class="stat-label">关键词数</span>
            </div>
          </NCard>
        </div>
      </div>

      <div class="quick-section">
        <div class="section-head">
          <h3 class="section-title">快速入口</h3>
          <p class="section-copy">从这里进入今天的阅读流、历史论文库和订阅维护。</p>
        </div>

        <div class="quick-grid">
          <NCard
            v-for="link in quickLinks"
            :key="link.path"
            class="quick-card"
            :bordered="false"
            hoverable
            @click="router.push(link.path)"
          >
            <div class="quick-icon">
              <NIcon :size="22"><component :is="link.icon" /></NIcon>
            </div>
            <div class="quick-body">
              <span class="quick-label">{{ link.label }}</span>
              <span class="quick-meta">{{ link.meta }}</span>
            </div>
          </NCard>
        </div>
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

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.9fr);
  gap: 20px;
  margin-bottom: 24px;
}

.hero-card {
  border-radius: 12px !important;
  padding: 4px;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%),
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.1), transparent 35%) !important;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #475569;
  margin-bottom: 18px;
}

.eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #2563eb;
}

.hero-title {
  margin: 0;
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: -0.03em;
  color: #0f172a;
  max-width: 16ch;
}

.hero-copy {
  margin: 14px 0 0;
  font-size: 15px;
  color: #475569;
  max-width: 52ch;
}

.hero-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.hero-tag {
  background: #eff6ff !important;
  color: #1d4ed8 !important;
}

.hero-inline-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid #e2e8f0;
}

.inline-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.inline-value {
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
  color: #0f172a;
}

.inline-label {
  font-size: 13px;
  color: #64748b;
}

.stats-stack {
  display: grid;
  gap: 14px;
}

.stat-card {
  border-radius: 12px !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
}

.stat-card :deep(.n-card__content) {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 24px !important;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #eff6ff;
  color: #1d4ed8;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 30px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}

.quick-section {
  margin-top: 28px;
}

.section-head {
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.section-copy {
  font-size: 14px;
  color: #64748b;
  margin-top: 6px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.quick-card {
  border-radius: 12px !important;
  cursor: pointer;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  transition: all 0.2s ease;
}

.quick-card:hover {
  border-color: #bfdbfe !important;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.06) !important;
  transform: translateY(-1px);
}

.quick-card :deep(.n-card__content) {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 20px !important;
}

.quick-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  color: #2563eb;
}

.quick-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quick-label {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.quick-meta {
  font-size: 13px;
  color: #64748b;
}

@media (max-width: 1024px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
  }

  .hero-inline-stats {
    grid-template-columns: 1fr;
  }
}
</style>
