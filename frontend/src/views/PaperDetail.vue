<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, NCard, NText, NSpace, NTag, NButton, NCollapse, NCollapseItem, NIcon, NSpin, NDivider } from 'naive-ui'
import { ArrowBackOutline, DocumentOutline, OpenOutline, CopyOutline, PeopleOutline, CalendarOutline, LinkOutline, BookOutline } from '@vicons/ionicons5'
import TagButtonGroup from '@/components/TagButtonGroup.vue'
import ScoreRing from '@/components/ScoreRing.vue'
import * as papersApi from '@/api/papers'
import type { Paper, TagType } from '@/types'

const route = useRoute()
const router = useRouter()
const msg = useMessage()
const loading = ref(true)
const paper = ref<Paper | null>(null)

const scoreItems = [
  { key: 'keyword_score', label: '关键词' },
  { key: 'personal_score', label: '个性化' },
  { key: 'prefilter_score', label: '预筛' },
  { key: 'final_score', label: '综合' },
]

const summaryLabels: Record<string, string> = {
  core_issue: '核心问题',
  innovation: '创新点',
  key_method: '关键方法',
  experiment_highlights: '实验亮点',
  recommendation_reason: '推荐理由',
}

async function fetchPaper() {
  loading.value = true
  try {
    const { data } = await papersApi.getPaper(Number(route.params.id))
    paper.value = data
  } catch {
    msg.error('加载失败')
    router.push('/papers')
  } finally {
    loading.value = false
  }
}

async function handleTag(type: TagType) {
  if (!paper.value) return
  try {
    await papersApi.addTag(paper.value.id, type)
    paper.value = { ...paper.value, tag_type: type } as any
    msg.success('已标记')
  } catch {
    msg.error('标记失败')
  }
}

async function handleRemoveTag() {
  if (!paper.value) return
  try {
    await papersApi.removeTag(paper.value.id)
    paper.value = { ...paper.value, tag_type: null } as any
    msg.success('已取消')
  } catch {
    msg.error('取消失败')
  }
}

function copyId() {
  if (paper.value) {
    navigator.clipboard.writeText(String(paper.value.id))
    msg.success('已复制 ID')
  }
}

onMounted(fetchPaper)
</script>

<template>
  <div>
    <NButton quaternary @click="router.back()" class="back-btn">
      <template #icon><NIcon :component="ArrowBackOutline" /></template>
      返回
    </NButton>

    <div v-if="loading" class="loading-state">
      <NSpin size="large" />
    </div>

    <template v-else-if="paper">
      <div class="detail-grid">
        <div class="detail-main">
          <NCard class="main-card" :bordered="true">
            <h1 class="paper-title">{{ paper.title }}</h1>

            <div class="paper-meta">
              <NTag v-if="paper.venue" type="success" size="small" :bordered="false" round>{{ paper.venue }}</NTag>
              <NTag v-else-if="paper.venue_hint" type="warning" size="small" :bordered="false" round>{{ paper.venue_hint }}（录用指向）</NTag>
              <NTag v-if="paper.bucket" size="small" :bordered="false" round :type="paper.bucket === 'venue' ? 'info' : 'success'">
                {{ paper.bucket === 'venue' ? '顶会桶' : 'arXiv 桶' }}
              </NTag>
            </div>

            <div class="authors-row">
              <NIcon :size="14" color="#9ca3af"><PeopleOutline /></NIcon>
              <span>{{ paper.authors?.join(', ') || '未知作者' }}</span>
            </div>

            <NDivider />

            <div v-if="paper.summary_cn && typeof paper.summary_cn === 'object'" class="summary-section">
              <h3 class="section-title">AI 结构化分析</h3>
              <div class="summary-grid">
                <div v-for="(label, key) in summaryLabels" :key="key" class="summary-item" v-show="(paper.summary_cn as any)?.[key]">
                  <span class="summary-label">{{ label }}</span>
                  <p class="summary-text">{{ (paper.summary_cn as any)[key] }}</p>
                </div>
              </div>
            </div>

            <div v-if="paper.llm_reason" class="llm-section">
              <h3 class="section-title">LLM 推荐理由</h3>
              <div class="llm-box">
                <p>{{ paper.llm_reason }}</p>
              </div>
            </div>

            <NCollapse class="abstract-collapse">
              <NCollapseItem title="中文摘要" name="cn">
                <p class="abstract-text">{{ paper.abstract_cn || '暂无' }}</p>
              </NCollapseItem>
              <NCollapseItem title="英文摘要" name="en">
                <p class="abstract-text">{{ paper.abstract_en || '暂无' }}</p>
              </NCollapseItem>
            </NCollapse>
          </NCard>
        </div>

        <div class="detail-side">
          <NCard class="side-card" :bordered="true">
            <h3 class="side-title">评分详情</h3>
            <div class="scores-row">
              <ScoreRing
                v-for="item in scoreItems"
                :key="item.key"
                :score="(paper as any)[item.key] || 0"
                :label="item.label"
                :size="56"
              />
            </div>
            <div v-if="paper.llm_score !== null" class="llm-score">
              <span class="llm-score-label">LLM 评分</span>
              <span class="llm-score-value">{{ paper.llm_score?.toFixed(1) }} / 10</span>
            </div>
          </NCard>

          <NCard class="side-card" :bordered="true">
            <h3 class="side-title">反馈</h3>
            <TagButtonGroup
              :tag-type="(paper as any).tag_type"
              @tag="handleTag"
              @remove="handleRemoveTag"
            />
          </NCard>

          <NCard class="side-card" :bordered="true">
            <h3 class="side-title">链接</h3>
            <div class="link-list">
              <NButton v-if="paper.pdf_url" block secondary tag="a" :href="paper.pdf_url" target="_blank">
                <template #icon><NIcon :component="DocumentOutline" /></template>
                PDF
              </NButton>
              <NButton block secondary @click="router.push(`/papers/${paper.id}/fulltext`)">
                <template #icon><NIcon :component="BookOutline" /></template>
                全文阅读 / 翻译
              </NButton>
              <NButton v-if="paper.url" block secondary tag="a" :href="paper.url" target="_blank">
                <template #icon><NIcon :component="OpenOutline" /></template>
                原文
              </NButton>
              <NButton v-if="paper.arxiv_id" block secondary tag="a" :href="`https://arxiv.org/abs/${paper.arxiv_id}`" target="_blank">
                <template #icon><NIcon :component="LinkOutline" /></template>
                arXiv: {{ paper.arxiv_id }}
              </NButton>
            </div>
          </NCard>

          <NCard class="side-card" :bordered="true">
            <h3 class="side-title">元数据</h3>
            <div class="meta-list">
              <div class="meta-row">
                <span class="meta-key">ID</span>
                <span class="meta-val" @click="copyId" style="cursor: pointer;">{{ paper.id }} <NIcon :size="12" :component="CopyOutline" /></span>
              </div>
              <div class="meta-row" v-if="paper.doi">
                <span class="meta-key">DOI</span>
                <span class="meta-val">{{ paper.doi }}</span>
              </div>
              <div class="meta-row" v-if="paper.arxiv_id">
                <span class="meta-key">arXiv</span>
                <span class="meta-val">{{ paper.arxiv_id }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-key">引用数</span>
                <span class="meta-val">{{ paper.citation_count }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-key">入库时间</span>
                <span class="meta-val">{{ paper.created_at?.split('T')[0] || 'N/A' }}</span>
              </div>
            </div>
          </NCard>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back-btn {
  margin-bottom: 20px;
  font-weight: 500;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  align-items: start;
}

.main-card {
  border-radius: 16px !important;
  border: 1px solid #f0f0f0 !important;
}

.paper-title {
  font-size: 22px;
  font-weight: 800;
  line-height: 1.4;
  margin: 0 0 12px;
  color: #111827;
  letter-spacing: -0.3px;
}

.paper-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.authors-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  font-size: 13px;
  color: #6b7280;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 14px;
}

.summary-section {
  margin-bottom: 24px;
}

.summary-grid {
  display: grid;
  gap: 10px;
}

.summary-item {
  padding: 12px 14px;
  background: #fafbfc;
  border-radius: 12px;
  border-left: 3px solid #6366f1;
}

.summary-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #6366f1;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.summary-text {
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
  margin: 0;
}

.llm-section {
  margin-bottom: 24px;
}

.llm-box {
  padding: 14px 16px;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border-radius: 12px;
  border-left: 3px solid #f59e0b;
}

.llm-box p {
  font-size: 14px;
  line-height: 1.6;
  color: #92400e;
  margin: 0;
}

.abstract-collapse {
  margin-top: 8px;
}

.abstract-text {
  font-size: 14px;
  line-height: 1.7;
  color: #4b5563;
  margin: 0;
}

.detail-side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.side-card {
  border-radius: 16px !important;
  border: 1px solid #f0f0f0 !important;
}

.side-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 14px;
}

.scores-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.llm-score {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.llm-score-label {
  font-size: 13px;
  color: #9ca3af;
}

.llm-score-value {
  font-size: 15px;
  font-weight: 700;
  color: #6366f1;
}

.link-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.meta-key {
  color: #9ca3af;
}

.meta-val {
  color: #374151;
  font-weight: 500;
}

@media (max-width: 1024px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
