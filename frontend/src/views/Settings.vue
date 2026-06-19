<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useMessage, NCard, NForm, NFormItem, NInput, NInputNumber, NSelect, NButton, NDivider, NSpin, NTag, NIcon } from 'naive-ui'
import { SaveOutline, SettingsOutline, SparklesOutline, TimeOutline } from '@vicons/ionicons5'
import PageHeader from '@/components/PageHeader.vue'
import SourceQuotaEditor from '@/components/SourceQuotaEditor.vue'
import * as settingsApi from '@/api/settings'
import type { SystemConfig, BucketConfig } from '@/types'

const msg = useMessage()
const loading = ref(true)
const saving = ref(false)
const config = ref<SystemConfig | null>(null)

const sourceSummary = computed(() => {
  const sources = config.value?.sources
  if (!sources) return ''
  return `${sources.daily_total} 篇 / ${sources.fill_policy === 'strict' ? 'strict' : 'spillover'}`
})

async function fetchSettings() {
  loading.value = true
  try {
    const { data } = await settingsApi.getSettings()
    config.value = data
  } catch {
    msg.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!config.value) return
  saving.value = true
  try {
    const { data } = await settingsApi.updateSettings(config.value)
    config.value = data
    msg.success('保存成功')
  } catch (err: any) {
    msg.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function handleBucketsUpdate(buckets: BucketConfig[]) {
  if (config.value) {
    config.value = { ...config.value, sources: { ...config.value.sources, buckets } }
  }
}

onMounted(fetchSettings)
</script>

<template>
  <div>
    <PageHeader title="系统设置" description="维护论文来源配额、LLM 成本边界和调度节奏。">
      <template #actions>
        <NButton type="primary" :loading="saving" :disabled="loading" @click="handleSave">
          <template #icon><NIcon :component="SaveOutline" /></template>
          保存配置
        </NButton>
      </template>
    </PageHeader>

    <div v-if="loading" class="loading-state">
      <NSpin size="large" />
    </div>

    <template v-else-if="config">
      <div class="settings-overview">
        <NCard class="overview-card overview-card-primary" :bordered="false">
          <div class="overview-icon">
            <NIcon :size="18"><SettingsOutline /></NIcon>
          </div>
          <div class="overview-body">
            <span class="overview-label">来源策略</span>
            <span class="overview-value">{{ sourceSummary }}</span>
          </div>
        </NCard>
        <NCard class="overview-card" :bordered="false">
          <div class="overview-icon">
            <NIcon :size="18"><SparklesOutline /></NIcon>
          </div>
          <div class="overview-body">
            <span class="overview-label">LLM 日预算</span>
            <span class="overview-value">${{ config.llm.daily_budget.toFixed(2) }}</span>
          </div>
        </NCard>
        <NCard class="overview-card" :bordered="false">
          <div class="overview-icon">
            <NIcon :size="18"><TimeOutline /></NIcon>
          </div>
          <div class="overview-body">
            <span class="overview-label">日报调度</span>
            <span class="overview-value">{{ config.scheduler.digest_cron }}</span>
          </div>
        </NCard>
      </div>

      <div class="settings-grid">
        <NCard class="settings-card" :bordered="false">
          <div class="card-head">
            <div>
              <h3 class="card-title">来源配额</h3>
              <p class="card-copy">控制 venue / arXiv 每日投喂量和补足策略。</p>
            </div>
            <NTag round :bordered="false" class="card-tag">Sources</NTag>
          </div>
          <NForm label-placement="left" label-width="100">
            <NFormItem label="每日总篇数">
              <NInputNumber v-model:value="config.sources.daily_total" :min="1" :max="20" style="width: 160px;" />
            </NFormItem>
            <NFormItem label="填充策略">
              <NSelect v-model:value="config.sources.fill_policy" :options="[
                { label: '宁缺毋滥 (strict)', value: 'strict' },
                { label: '跨桶补足 (spillover)', value: 'spillover' },
              ]" style="width: 220px;" />
            </NFormItem>
          </NForm>
          <NDivider />
          <SourceQuotaEditor :buckets="config.sources.buckets" @update="handleBucketsUpdate" />
        </NCard>

        <NCard class="settings-card" :bordered="false">
          <div class="card-head">
            <div>
              <h3 class="card-title">LLM 配置</h3>
              <p class="card-copy">约束预算、批量大小和熔断阈值，避免推送链路失控。</p>
            </div>
            <NTag round :bordered="false" class="card-tag">Budget</NTag>
          </div>
          <NForm label-placement="left" label-width="120">
            <NFormItem label="每日预算 (USD)">
              <NInputNumber v-model:value="config.llm.daily_budget" :min="0" :max="100" :step="0.1" style="width: 160px;" />
            </NFormItem>
            <NFormItem label="单次成本上限">
              <NInputNumber v-model:value="config.llm.max_cost_per_call" :min="0" :max="10" :step="0.01" style="width: 160px;" />
            </NFormItem>
            <NFormItem label="批量大小">
              <NInputNumber v-model:value="config.llm.batch_size" :min="1" :max="50" style="width: 160px;" />
            </NFormItem>
            <NFormItem label="熔断阈值">
              <NInputNumber v-model:value="config.llm.circuit_threshold" :min="1" :max="20" style="width: 160px;" />
            </NFormItem>
            <NFormItem label="冷却时间 (秒)">
              <NInputNumber v-model:value="config.llm.circuit_cooldown_sec" :min="60" :max="3600" :step="60" style="width: 160px;" />
            </NFormItem>
          </NForm>
        </NCard>

        <NCard class="settings-card" :bordered="false">
          <div class="card-head">
            <div>
              <h3 class="card-title">调度器</h3>
              <p class="card-copy">定义抓取和 digest 的执行节奏，保持输出稳定。</p>
            </div>
            <NTag round :bordered="false" class="card-tag">Scheduler</NTag>
          </div>
          <NForm label-placement="left" label-width="120">
            <NFormItem label="日报 Cron">
              <NInput v-model:value="config.scheduler.digest_cron" style="width: 220px;" />
            </NFormItem>
            <NFormItem label="抓取 Cron">
              <NInput v-model:value="config.scheduler.fetch_cron" style="width: 220px;" />
            </NFormItem>
          </NForm>
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

.settings-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.overview-card {
  border-radius: 12px !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
}

.overview-card-primary {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%),
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 35%) !important;
}

.overview-card :deep(.n-card__content) {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 20px !important;
}

.overview-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eff6ff;
  color: #1d4ed8;
  flex-shrink: 0;
}

.overview-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.overview-label {
  font-size: 12px;
  color: #64748b;
}

.overview-value {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-card {
  border-radius: 12px !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.card-copy {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
}

.card-tag {
  background: #f8fafc !important;
  color: #475569 !important;
  border: 1px solid #e2e8f0;
}

@media (max-width: 1024px) {
  .settings-overview {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .card-head {
    flex-direction: column;
  }
}
</style>
