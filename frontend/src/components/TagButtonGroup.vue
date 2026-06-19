<script setup lang="ts">
import { NButton, NIcon, NTooltip } from 'naive-ui'
import { ThumbsUpOutline, ThumbsDownOutline, BookmarkOutline } from '@vicons/ionicons5'
import type { TagType } from '@/types'

const props = defineProps<{
  tagType?: string | null
  size?: 'small' | 'medium'
}>()

const emit = defineEmits<{
  tag: [type: TagType]
  remove: []
}>()

const buttons: { type: TagType; label: string; icon: any; color: string; bg: string }[] = [
  { type: 'interested', label: '感兴趣', icon: ThumbsUpOutline, color: '#10b981', bg: '#ecfdf5' },
  { type: 'not_interested', label: '不感兴趣', icon: ThumbsDownOutline, color: '#ef4444', bg: '#fef2f2' },
  { type: 'read_later', label: '稍后阅读', icon: BookmarkOutline, color: '#f59e0b', bg: '#fffbeb' },
]

function handleClick(btn: typeof buttons[0]) {
  if (props.tagType === btn.type) {
    emit('remove')
  } else {
    emit('tag', btn.type)
  }
}
</script>

<template>
  <div class="tag-buttons">
    <NTooltip v-for="btn in buttons" :key="btn.type" trigger="hover">
      <template #trigger>
        <NButton
          :size="size || 'medium'"
          :style="tagType === btn.type ? { background: btn.bg, color: btn.color, border: `1px solid ${btn.color}20` } : {}"
          :type="tagType === btn.type ? 'default' : 'default'"
          :quaternary="tagType !== btn.type"
          @click.stop="handleClick(btn)"
          round
        >
          <template #icon><NIcon :component="btn.icon" /></template>
        </NButton>
      </template>
      {{ btn.label }}
    </NTooltip>
  </div>
</template>

<style scoped>
.tag-buttons {
  display: flex;
  gap: 6px;
}
</style>
