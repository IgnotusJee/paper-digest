<script setup lang="ts">
import { NEmpty, NIcon } from 'naive-ui'

defineProps<{
  description?: string
}>()
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <rect x="8" y="12" width="48" height="40" rx="8" stroke="#d1d5db" stroke-width="2" fill="none"/>
        <path d="M20 28h24M20 36h16" stroke="#d1d5db" stroke-width="2" stroke-linecap="round"/>
        <circle cx="32" cy="20" r="4" fill="#d1d5db"/>
      </svg>
    </div>
    <p class="empty-text">{{ description || '暂无数据' }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-text {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}
</style>
