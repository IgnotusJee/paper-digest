<script setup lang="ts">
import { NIcon, NText } from 'naive-ui'
import { computed } from 'vue'

const props = defineProps<{
  score: number
  maxScore?: number
  label: string
  size?: number
}>()

const percentage = computed(() => {
  const max = props.maxScore ?? 10
  return Math.round((props.score / max) * 100)
})

const color = computed(() => {
  if (percentage.value >= 70) return '#22c55e'
  if (percentage.value >= 40) return '#f59e0b'
  return '#ef4444'
})

const circumference = computed(() => 2 * Math.PI * 36)
const dashoffset = computed(() => circumference.value * (1 - percentage.value / 100))
</script>

<template>
  <div class="score-ring" :style="{ width: `${size || 64}px`, height: `${size || 64}px` }">
    <svg viewBox="0 0 80 80">
      <circle cx="40" cy="40" r="36" fill="none" stroke="#e2e8f0" stroke-width="6" />
      <circle
        cx="40" cy="40" r="36" fill="none"
        :stroke="color"
        stroke-width="6"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashoffset"
        transform="rotate(-90 40 40)"
        style="transition: stroke-dashoffset 0.6s ease"
      />
    </svg>
    <div class="score-text">
      <NText strong style="font-size: 14px;">{{ score.toFixed(1) }}</NText>
    </div>
    <NText depth="3" style="font-size: 11px; text-align: center; margin-top: 2px;">{{ label }}</NText>
  </div>
</template>

<style scoped>
.score-ring {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}
.score-ring svg {
  width: 100%;
  height: 100%;
}
.score-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -60%);
}
</style>
