<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage, NCard, NForm, NFormItem, NInput, NInputNumber, NSelect, NButton, NSpace, NDivider, NSpin } from 'naive-ui'
import PageHeader from '@/components/PageHeader.vue'
import SourceQuotaEditor from '@/components/SourceQuotaEditor.vue'
import * as settingsApi from '@/api/settings'
import type { SystemConfig, BucketConfig } from '@/types'

const msg = useMessage()
const loading = ref(true)
const saving = ref(false)
const config = ref<SystemConfig | null>(null)

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
    <PageHeader title="系统设置" description="配置推荐引擎、LLM、调度器等参数">
      <template #actions>
        <NButton type="primary" :loading="saving" :disabled="loading" @click="handleSave" round>
          保存配置
        </NButton>
      </template>
    </PageHeader>

    <div v-if="loading" class="loading-state">
      <NSpin size="large" />
    </div>

    <template v-else-if="config">
      <div class="settings-grid">
        <NCard class="settings-card" :bordered="true">
          <h3 class="card-title">来源配额</h3>
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

        <NCard class="settings-card" :bordered="true">
          <h3 class="card-title">LLM 配置</h3>
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

        <NCard class="settings-card" :bordered="true">
          <h3 class="card-title">调度器</h3>
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

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-card {
  border-radius: 16px !important;
  border: 1px solid #f0f0f0 !important;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 20px;
}
</style>
