<template>
  <div class="score-container">
    <div class="score-row">
      <span class="label">综合得分:</span>
      <span class="value final">{{ finalScore.toFixed(2) }}</span>
    </div>
    <div class="score-grid">
      <div class="score-item">
        <span class="sub-label">关键词匹配:</span>
        <n-progress
          type="line"
          :percentage="keywordPercentage"
          :show-indicator="false"
          status="success"
          processing
          style="width: 80px;"
        />
        <span class="sub-val">{{ keywordScore.toFixed(2) }}</span>
      </div>
      <div class="score-item">
        <span class="sub-label">个人偏好:</span>
        <n-progress
          type="line"
          :percentage="personalPercentage"
          :show-indicator="false"
          status="info"
          style="width: 80px;"
        />
        <span class="sub-val">{{ personalScore.toFixed(2) }}</span>
      </div>
      <div class="score-item">
        <span class="sub-label">初步筛选:</span>
        <n-progress
          type="line"
          :percentage="prefilterPercentage"
          :show-indicator="false"
          status="warning"
          style="width: 80px;"
        />
        <span class="sub-val">{{ prefilterScore.toFixed(2) }}</span>
      </div>
      <div class="score-item">
        <span class="sub-label">LLM 打分:</span>
        <n-progress
          type="line"
          :percentage="llmPercentage"
          :show-indicator="false"
          :status="llmScore > 0 ? 'error' : 'default'"
          style="width: 80px;"
        />
        <span class="sub-val">{{ llmScore.toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  finalScore: number;
  keywordScore: number;
  personalScore: number;
  prefilterScore: number;
  llmScore: number;
}>();

const keywordPercentage = computed(() => Math.min(Math.max(props.keywordScore * 100, 0), 100));
const personalPercentage = computed(() => Math.min(Math.max(props.personalScore * 100, 0), 100));
const prefilterPercentage = computed(() => Math.min(Math.max(props.prefilterScore * 100, 0), 100));
const llmPercentage = computed(() => Math.min(Math.max((props.llmScore / 10) * 100, 0), 100));
</script>

<style scoped>
.score-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px;
  background-color: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
.score-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}
.value.final {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.score-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.score-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}
.sub-label {
  color: #64748b;
  width: 60px;
}
.sub-val {
  font-weight: 600;
  color: #334155;
  width: 30px;
  text-align: right;
}
</style>
