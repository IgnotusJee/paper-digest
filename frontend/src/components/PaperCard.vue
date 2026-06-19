<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NTag, NText, NSpace, NIcon, NButton } from 'naive-ui'
import { ChevronDownOutline, OpenOutline, DocumentOutline, PeopleOutline } from '@vicons/ionicons5'
import TagButtonGroup from './TagButtonGroup.vue'
import type { PaperListItem, DigestPaper, TagType } from '@/types'

const props = defineProps<{
  paper: PaperListItem | DigestPaper
  showAbstract?: boolean
  compact?: boolean
}>()

const emit = defineEmits<{
  tag: [paperId: number, type: TagType]
  remove: [paperId: number]
  click: [paperId: number]
}>()

const expanded = ref(false)

const venueLabel = computed(() => {
  const p = props.paper
  if (p.venue) return p.venue
  if (p.venue_hint) return `${p.venue_hint}（录用指向）`
  return null
})

const venueType = computed(() => {
  if (props.paper.venue) return 'success' as const
  if (props.paper.venue_hint) return 'warning' as const
  return undefined
})

const abstractText = computed(() => {
  const p = props.paper as any
  return p.abstract_cn || null
})

const summaryFields = computed(() => {
  const p = props.paper as any
  if (!p.summary_cn || typeof p.summary_cn !== 'object') return []
  const labels: Record<string, string> = {
    core_issue: '核心问题',
    innovation: '创新点',
    key_method: '关键方法',
    experiment_highlights: '实验亮点',
    recommendation_reason: '推荐理由',
  }
  return Object.entries(labels)
    .filter(([k]) => p.summary_cn[k])
    .map(([k, label]) => ({ label, value: p.summary_cn[k] }))
})

const shortAuthors = computed(() => {
  const authors = (props.paper as any).authors
  if (!authors?.length) return ''
  const first3 = authors.slice(0, 3).join(', ')
  return authors.length > 3 ? `${first3} 等` : first3
})

function handleTag(type: TagType) {
  emit('tag', props.paper.id, type)
}

function handleRemove() {
  emit('remove', props.paper.id)
}
</script>

<template>
  <NCard
    :class="['paper-card', { compact }]"
    :bordered="true"
    size="small"
    @click="emit('click', paper.id)"
  >
    <div class="card-top">
      <div class="card-title-row">
        <h3 class="paper-title">{{ paper.title }}</h3>
        <div class="card-score">
          <span class="score-value">{{ paper.final_score.toFixed(2) }}</span>
        </div>
      </div>

      <div class="card-tags">
        <NTag v-if="venueLabel" :type="venueType" size="small" :bordered="false" round>
          {{ venueLabel }}
        </NTag>
        <NTag
          v-if="paper.bucket"
          size="small"
          :bordered="false"
          round
          :type="paper.bucket === 'venue' ? 'info' : 'success'"
        >
          {{ paper.bucket === 'venue' ? '顶会' : 'arXiv' }}
        </NTag>
      </div>

      <div class="card-meta" v-if="shortAuthors">
        <NIcon :size="14" color="#9ca3af"><PeopleOutline /></NIcon>
        <span class="meta-text">{{ shortAuthors }}</span>
        <template v-if="(paper as any).year">
          <span class="meta-dot">·</span>
          <span class="meta-text">{{ (paper as any).year }}</span>
        </template>
      </div>
    </div>

    <div v-if="showAbstract && (abstractText || summaryFields.length)" class="card-body" @click.stop>
      <button class="expand-btn" @click.stop="expanded = !expanded">
        <NIcon :size="14" :style="{ transform: expanded ? 'rotate(180deg)' : '', transition: 'transform 0.25s ease' }">
          <ChevronDownOutline />
        </NIcon>
        <span>{{ expanded ? '收起摘要' : '展开摘要' }}</span>
      </button>

      <transition name="expand">
        <div v-if="expanded" class="expand-content">
          <div v-if="summaryFields.length" class="summary-grid">
            <div v-for="field in summaryFields" :key="field.label" class="summary-item">
              <span class="summary-label">{{ field.label }}</span>
              <p class="summary-text">{{ field.value }}</p>
            </div>
          </div>
          <p v-else-if="abstractText" class="abstract-text">{{ abstractText }}</p>
        </div>
      </transition>
    </div>

    <div class="card-footer" @click.stop>
      <TagButtonGroup
        :tag-type="(paper as any).tag_type"
        size="small"
        @tag="handleTag"
        @remove="handleRemove"
      />
      <div class="card-links">
        <NButton v-if="(paper as any).pdf_url" quaternary size="tiny" tag="a" :href="(paper as any).pdf_url" target="_blank" @click.stop>
          <template #icon><NIcon :size="16" :component="DocumentOutline" /></template>
        </NButton>
        <NButton v-if="(paper as any).url" quaternary size="tiny" tag="a" :href="(paper as any).url" target="_blank" @click.stop>
          <template #icon><NIcon :size="16" :component="OpenOutline" /></template>
        </NButton>
      </div>
    </div>
  </NCard>
</template>

<style scoped>
.paper-card {
  border-radius: 14px !important;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid #f0f0f0 !important;
}

.paper-card:hover {
  border-color: #e0e7ff !important;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.08) !important;
  transform: translateY(-2px);
}

.paper-card.compact {
  margin-bottom: 0;
}

.card-top {
  margin-bottom: 4px;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.paper-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.5;
  margin: 0;
  flex: 1;
  color: #111827;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-score {
  flex-shrink: 0;
}

.score-value {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  height: 28px;
  padding: 0 8px;
  border-radius: 8px;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  color: #6366f1;
  font-size: 13px;
  font-weight: 700;
}

.card-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}

.meta-text {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.4;
}

.meta-dot {
  color: #d1d5db;
  font-size: 12px;
}

.card-body {
  border-top: 1px solid #f3f4f6;
  margin-top: 12px;
  padding-top: 8px;
}

.expand-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  background: none;
  color: #6366f1;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.expand-btn:hover {
  background: #eef2ff;
}

.expand-content {
  margin-top: 8px;
}

.summary-grid {
  display: grid;
  gap: 8px;
}

.summary-item {
  padding: 10px 12px;
  background: #fafbfc;
  border-radius: 10px;
  border-left: 3px solid #6366f1;
}

.summary-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #6366f1;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.summary-text {
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
  margin: 0;
}

.abstract-text {
  font-size: 13px;
  line-height: 1.7;
  color: #4b5563;
  margin: 0;
  padding: 8px 12px;
  background: #fafbfc;
  border-radius: 8px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f3f4f6;
}

.card-links {
  display: flex;
  gap: 2px;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}

@media (max-width: 768px) {
  .paper-title {
    font-size: 14px;
  }

  .card-title-row {
    gap: 10px;
  }
}
</style>
