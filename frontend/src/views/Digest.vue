<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NDatePicker, NTag, NText, NIcon, NSpin, NAlert, NBadge } from 'naive-ui'
import { AlertCircleOutline, NewspaperOutline } from '@vicons/ionicons5'
import PageHeader from '@/components/PageHeader.vue'
import PaperCard from '@/components/PaperCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import * as digestApi from '@/api/digest'
import * as papersApi from '@/api/papers'
import type { DigestHistory, DigestPaper, TagType } from '@/types'

const router = useRouter()
const msg = useMessage()
const loading = ref(true)
const digest = ref<DigestHistory | null>(null)
const selectedDate = ref<number | null>(null)

const venuePapers = computed(() =>
  (digest.value?.papers || []).filter(p => p.bucket === 'venue')
)
const arxivPapers = computed(() =>
  (digest.value?.papers || []).filter(p => p.bucket === 'arxiv')
)

async function fetchDigest(date?: string) {
  loading.value = true
  try {
    const { data } = date ? await digestApi.getDigestByDate(date) : await digestApi.getTodayDigest()
    digest.value = data
  } catch (err: any) {
    if (err.response?.status === 404) {
      digest.value = null
    } else {
      msg.error('加载失败')
    }
  } finally {
    loading.value = false
  }
}

function handleDateChange(value: number | null) {
  selectedDate.value = value
  if (value) {
    const d = new Date(value)
    const dateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    fetchDigest(dateStr)
  } else {
    fetchDigest()
  }
}

async function handleTag(paperId: number, type: TagType) {
  try {
    await papersApi.addTag(paperId, type)
    const paper = digest.value?.papers.find(p => p.id === paperId)
    if (paper) (paper as any).tag_type = type
    msg.success('已标记')
  } catch {
    msg.error('标记失败')
  }
}

async function handleRemoveTag(paperId: number) {
  try {
    await papersApi.removeTag(paperId)
    const paper = digest.value?.papers.find(p => p.id === paperId)
    if (paper) (paper as any).tag_type = null
    msg.success('已取消标记')
  } catch {
    msg.error('取消失败')
  }
}

function goToDetail(paperId: number) {
  router.push(`/papers/${paperId}`)
}

onMounted(() => fetchDigest())
</script>

<template>
  <div>
    <PageHeader title="今日推荐" description="每日精选论文，按来源分组展示">
      <template #actions>
        <NDatePicker
          :value="selectedDate"
          type="date"
          @update:value="handleDateChange"
          placeholder="选择日期"
          style="width: 180px;"
        />
      </template>
    </PageHeader>

    <div v-if="loading" class="loading-state">
      <NSpin size="large" />
    </div>

    <template v-else-if="digest">
      <NAlert v-if="digest.degraded" type="warning" :bordered="false" class="degraded-alert">
        <template #icon><NIcon :component="AlertCircleOutline" /></template>
        本次推荐未经 LLM 精排，已降级为预筛排序
      </NAlert>

      <div class="digest-meta">
        <NTag :type="digest.status === 'sent' ? 'success' : 'error'" size="small" :bordered="false" round>
          {{ digest.status === 'sent' ? '已发送' : '发送失败' }}
        </NTag>
        <span class="meta-date">{{ digest.date }}</span>
        <span class="meta-count">{{ digest.papers.length }} 篇论文</span>
      </div>

      <div class="buckets-grid">
        <div class="bucket-col">
          <div class="bucket-header">
            <div class="bucket-label">
              <NTag type="info" size="small" :bordered="false" round>顶会/顶刊</NTag>
              <span class="bucket-count">{{ venuePapers.length }} 篇</span>
            </div>
          </div>
          <div class="paper-list">
            <PaperCard
              v-for="paper in venuePapers"
              :key="paper.id"
              :paper="paper"
              show-abstract
              @tag="handleTag"
              @remove="handleRemoveTag"
              @click="goToDetail"
            />
            <EmptyState v-if="!venuePapers.length" description="今日无顶会论文" />
          </div>
        </div>

        <div class="bucket-col">
          <div class="bucket-header">
            <div class="bucket-label">
              <NTag type="success" size="small" :bordered="false" round>arXiv</NTag>
              <span class="bucket-count">{{ arxivPapers.length }} 篇</span>
            </div>
          </div>
          <div class="paper-list">
            <PaperCard
              v-for="paper in arxivPapers"
              :key="paper.id"
              :paper="paper"
              show-abstract
              @tag="handleTag"
              @remove="handleRemoveTag"
              @click="goToDetail"
            />
            <EmptyState v-if="!arxivPapers.length" description="今日无 arXiv 论文" />
          </div>
        </div>
      </div>
    </template>

    <EmptyState v-else description="今日暂无推荐，等待定时任务生成" />
  </div>
</template>

<style scoped>
.loading-state {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}

.degraded-alert {
  border-radius: 12px !important;
  margin-bottom: 20px;
}

.digest-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 24px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #f0f0f0;
}

.meta-date {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.meta-count {
  font-size: 13px;
  color: #9ca3af;
  margin-left: auto;
}

.buckets-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.bucket-header {
  margin-bottom: 16px;
}

.bucket-label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bucket-count {
  font-size: 13px;
  color: #9ca3af;
}

.paper-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 1024px) {
  .buckets-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .digest-meta {
    flex-wrap: wrap;
    gap: 8px;
  }

  .meta-count {
    margin-left: 0;
    width: 100%;
  }
}
</style>
