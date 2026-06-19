<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NSwitch, NSlider, NText, NSpace, NTag, NInputGroup, NButton, NIcon, useMessage, NInput } from 'naive-ui'
import { AddCircleOutline } from '@vicons/ionicons5'
import type { BucketConfig } from '@/types'

const props = defineProps<{
  buckets: BucketConfig[]
}>()

const emit = defineEmits<{
  update: [buckets: BucketConfig[]]
}>()

const msg = useMessage()
const venueDraft = ref('')
const categoryDraft = ref('')

function updateBucket(index: number, patch: Partial<BucketConfig>) {
  const updated = [...props.buckets]
  const existing = updated[index]
  if (!existing) return
  updated[index] = { ...existing, ...patch } as BucketConfig
  emit('update', updated)
}

function addVenue(bucketIndex: number) {
  const v = venueDraft.value.trim().toUpperCase()
  if (!v) return
  const bucket = props.buckets[bucketIndex]
  if (!bucket) return
  if (bucket.venues?.includes(v)) {
    msg.warning('已存在')
    return
  }
  updateBucket(bucketIndex, { venues: [...(bucket.venues || []), v] })
  venueDraft.value = ''
}

function removeVenue(bucketIndex: number, venue: string) {
  const bucket = props.buckets[bucketIndex]
  if (!bucket) return
  updateBucket(bucketIndex, { venues: (bucket.venues || []).filter(v => v !== venue) })
}

function addCategory(bucketIndex: number) {
  const c = categoryDraft.value.trim()
  if (!c) return
  const bucket = props.buckets[bucketIndex]
  if (!bucket) return
  if (bucket.arxiv_categories?.includes(c)) {
    msg.warning('已存在')
    return
  }
  updateBucket(bucketIndex, { arxiv_categories: [...(bucket.arxiv_categories || []), c] })
  categoryDraft.value = ''
}

function removeCategory(bucketIndex: number, cat: string) {
  const bucket = props.buckets[bucketIndex]
  if (!bucket) return
  updateBucket(bucketIndex, { arxiv_categories: (bucket.arxiv_categories || []).filter(c => c !== cat) })
}
</script>

<template>
  <div class="source-quota-editor">
    <NCard v-for="(bucket, idx) in buckets" :key="bucket.name" class="bucket-card" :title="bucket.name === 'venue' ? '顶会/顶刊' : 'arXiv'" size="small">
      <template #header-extra>
        <NSwitch :value="bucket.enabled" @update:value="v => updateBucket(idx, { enabled: v })" />
      </template>

      <NSpace vertical :size="12">
        <div>
          <NText depth="3" style="font-size: 13px; display: block; margin-bottom: 4px;">每日配额</NText>
          <NSlider :value="bucket.quota" :min="0" :max="10" :step="1" @update:value="v => updateBucket(idx, { quota: v })" style="max-width: 300px;" />
          <NText style="font-size: 13px; margin-top: 4px; display: block;">{{ bucket.quota }} 篇</NText>
        </div>

        <div v-if="bucket.venues">
          <NText depth="3" style="font-size: 13px; display: block; margin-bottom: 6px;">会议/期刊列表</NText>
          <NSpace :size="6" class="token-wrap">
            <NTag v-for="v in bucket.venues" :key="v" size="small" closable round class="bucket-tag" @close="removeVenue(idx, v)">{{ v }}</NTag>
          </NSpace>
          <NInputGroup class="bucket-input-group">
            <NInput v-model:value="venueDraft" placeholder="添加会议缩写" @keyup.enter="addVenue(idx)" />
            <NButton size="small" @click="addVenue(idx)">
              <template #icon><NIcon :component="AddCircleOutline" /></template>
            </NButton>
          </NInputGroup>
        </div>

        <div v-if="bucket.arxiv_categories">
          <NText depth="3" style="font-size: 13px; display: block; margin-bottom: 6px;">arXiv 分类</NText>
          <NSpace :size="6" class="token-wrap">
            <NTag v-for="c in bucket.arxiv_categories" :key="c" size="small" closable round class="bucket-tag" @close="removeCategory(idx, c)">{{ c }}</NTag>
          </NSpace>
          <NInputGroup class="bucket-input-group">
            <NInput v-model:value="categoryDraft" placeholder="添加分类 (如 cs.LG)" @keyup.enter="addCategory(idx)" />
            <NButton size="small" @click="addCategory(idx)">
              <template #icon><NIcon :component="AddCircleOutline" /></template>
            </NButton>
          </NInputGroup>
        </div>
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.source-quota-editor {
  display: grid;
  gap: 16px;
}

.bucket-card {
  border-radius: 12px !important;
  border: 1px solid #e2e8f0 !important;
}

.token-wrap {
  flex-wrap: wrap;
}

.bucket-tag {
  background: #f8fafc !important;
  color: #334155 !important;
  border: 1px solid #e2e8f0;
}

.bucket-input-group {
  margin-top: 8px;
  max-width: 320px;
}
</style>
