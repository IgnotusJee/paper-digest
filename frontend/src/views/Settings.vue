<template>
  <div class="settings-view">
    <n-spin :show="loading">
      <div v-if="config" class="settings-container">
        <n-space vertical size="large">
          <!-- Source Quota Buckets -->
          <n-card title="📊 来源配额设置">
            <n-form label-placement="left" label-width="120px">
              <n-form-item label="每日推荐总篇数">
                <n-input-number v-model:value="config.sources.daily_total" :min="1" :max="50" style="width: 150px;" />
              </n-form-item>
              <n-form-item label="回填策略 (policy)">
                <n-select
                  v-model:value="config.sources.fill_policy"
                  :options="fillPolicyOptions"
                  style="width: 200px;"
                />
                <div style="font-size: 12px; color: #64748b; margin-left: 12px;">
                  strict: 宁缺毋滥 (配额不足时不补位)；spillover: 允许其他桶补足总数。
                </div>
              </n-form-item>
              <n-form-item label="超额候选倍数">
                <n-input-number v-model:value="config.sources.oversample" :min="1" :max="10" style="width: 150px;" />
              </n-form-item>
            </n-form>
            <n-divider />
            <source-quota-editor :buckets="config.sources.buckets" />
          </n-card>

          <!-- Prefilter Scoring Weights -->
          <n-card title="🎯 预筛权重配置">
            <div style="font-size: 13px; color: #64748b; margin-bottom: 16px;">
              第一级预筛选中，各维度打分的加权比重（权重之和无需为 1，系统会自动按比例归一化）。
            </div>
            <n-form label-placement="left" label-width="150px">
              <n-form-item label="关键词匹配权重">
                <div class="weight-slider-row">
                  <n-slider v-model:value="config.scoring.prefilter.keyword" :min="0" :max="1.0" :step="0.05" />
                  <n-input-number v-model:value="config.scoring.prefilter.keyword" :min="0" :max="1.0" :step="0.05" size="small" />
                </div>
              </n-form-item>
              <n-form-item label="个人偏好匹配权重">
                <div class="weight-slider-row">
                  <n-slider v-model:value="config.scoring.prefilter.personal" :min="0" :max="1.0" :step="0.05" />
                  <n-input-number v-model:value="config.scoring.prefilter.personal" :min="0" :max="1.0" :step="0.05" size="small" />
                </div>
              </n-form-item>
              <n-form-item label="时间衰减权重">
                <div class="weight-slider-row">
                  <n-slider v-model:value="config.scoring.prefilter.recency" :min="0" :max="1.0" :step="0.05" />
                  <n-input-number v-model:value="config.scoring.prefilter.recency" :min="0" :max="1.0" :step="0.05" size="small" />
                </div>
              </n-form-item>
              <n-form-item label="来源先验权重">
                <div class="weight-slider-row">
                  <n-slider v-model:value="config.scoring.prefilter.source_prior" :min="0" :max="1.0" :step="0.05" />
                  <n-input-number v-model:value="config.scoring.prefilter.source_prior" :min="0" :max="1.0" :step="0.05" size="small" />
                </div>
              </n-form-item>
            </n-form>
          </n-card>

          <!-- Recommender Centroid config -->
          <n-card title="🧠 推荐模型门控 (Recommender)">
            <n-form label-placement="left" label-width="180px">
              <n-form-item label="质心模式最小正反馈">
                <n-input-number v-model:value="config.recommender.min_pos_centroid" :min="1" :max="100" />
              </n-form-item>
              <n-form-item label="分类模型最小正反馈">
                <n-input-number v-model:value="config.recommender.min_pos_model" :min="5" :max="500" />
              </n-form-item>
              <n-form-item label="分类模型最小负反馈">
                <n-input-number v-model:value="config.recommender.min_neg_model" :min="5" :max="500" />
              </n-form-item>
            </n-form>
          </n-card>

          <!-- LLM budget/circuits -->
          <n-card title="🤖 LLM 研排与成本设置">
            <n-form label-placement="left" label-width="150px">
              <n-form-item label="LLM 降级链 (chain)">
                <n-dynamic-tags v-model:value="config.llm.chain" />
                <template #feedback>
                  模型降级顺序，例如: deepseek, kimi
                </template>
              </n-form-item>
              
              <n-form-item label="每日预算上限 (¥)">
                <n-input-number v-model:value="config.llm.daily_budget" :min="0" :max="10.0" :step="0.05" style="width: 150px;" />
                <div style="font-size: 12px; color: #64748b; margin-left: 12px;">
                  当本日 LLM 累计消费超过此限额时，将自动熔断，次日报降级为预筛排序。
                </div>
              </n-form-item>
              
              <n-form-item label="单次请求上限 (¥)">
                <n-input-number v-model:value="config.llm.max_cost_per_call" :min="0" :max="2.0" :step="0.01" style="width: 150px;" />
              </n-form-item>
              
              <n-form-item label="精排单批最大篇数">
                <n-input-number v-model:value="config.llm.batch_size" :min="1" :max="30" style="width: 150px;" />
              </n-form-item>
              
              <n-form-item label="服务连续熔断阈值">
                <n-input-number v-model:value="config.llm.circuit_threshold" :min="1" :max="10" style="width: 150px;" />
              </n-form-item>
              
              <n-form-item label="熔断冷却时间 (秒)">
                <n-input-number v-model:value="config.llm.circuit_cooldown_sec" :min="60" :max="3600" :step="60" style="width: 150px;" />
              </n-form-item>
            </n-form>
          </n-card>

          <!-- Scheduler configuration (Read-only representation) -->
          <n-card title="⏰ 定时任务周期">
            <n-form label-placement="left" label-width="150px">
              <n-form-item label="抓取任务 (Cron)">
                <n-input v-model:value="config.scheduler.fetch_cron" placeholder="例如: 30 */6 * * *" />
              </n-form-item>
              <n-form-item label="日报生成与推送 (Cron)">
                <n-input v-model:value="config.scheduler.digest_cron" placeholder="例如: 0 9 * * *" />
              </n-form-item>
            </n-form>
          </n-card>

          <!-- Actions -->
          <n-card>
            <n-space justify="end">
              <n-button type="primary" size="large" :loading="saveLoading" @click="saveSettings">
                保存配置
              </n-button>
            </n-space>
          </n-card>
        </n-space>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { SystemConfig } from '../types';
import { settingsApi } from '../api/settings';
import SourceQuotaEditor from '../components/SourceQuotaEditor.vue';
import { useMessage } from 'naive-ui';

const config = ref<SystemConfig | null>(null);
const loading = ref(false);
const saveLoading = ref(false);
const message = useMessage();

const fillPolicyOptions = [
  { label: '宁缺毋滥 (strict)', value: 'strict' },
  { label: '其他桶补足 (spillover)', value: 'spillover' }
];

onMounted(() => {
  fetchSettings();
});

async function fetchSettings() {
  loading.value = true;
  try {
    const res = await settingsApi.get();
    config.value = res.data;
  } catch (err) {
    message.error('获取系统设置失败');
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  if (!config.value) return;
  saveLoading.value = true;
  try {
    const res = await settingsApi.update(config.value);
    config.value = res.data;
    message.success('配置已保存');
  } catch (err: any) {
    const errMsg = err.response?.data?.detail || '保存配置失败';
    message.error(errMsg);
  } finally {
    saveLoading.value = false;
  }
}
</script>

<style scoped>
.settings-view {
  max-width: 900px;
  margin: 0 auto;
}
.weight-slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}
.weight-slider-row .n-slider {
  flex: 1;
}
</style>
