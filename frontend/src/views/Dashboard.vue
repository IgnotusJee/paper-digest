<template>
  <div class="dashboard-view">
    <n-spin :show="loading">
      <n-space vertical size="large">
        <!-- Welcoming Alert -->
        <n-alert title="欢迎使用 AI 论文日报系统" type="info" :bordered="false">
          每日早上 09:00 定时执行抓取与评分推送任务。您可以管理个性化筛选关键词及配额分配。
        </n-alert>

        <!-- Stats Grid Cards -->
        <n-grid cols="1 s:2 m:4 l:4" responsive="screen" :x-gap="16" :y-gap="16">
          <n-grid-item>
            <n-card>
              <n-statistic label="论文库总计" :value="stats.totalPapers">
                <template #prefix>📄</template>
                <template #suffix>篇</template>
              </n-statistic>
            </n-card>
          </n-grid-item>

          <n-grid-item>
            <n-card>
              <n-statistic label="收录关键词" :value="stats.totalKeywords">
                <template #prefix>🔑</template>
                <template #suffix>个</template>
              </n-statistic>
            </n-card>
          </n-grid-item>

          <n-grid-item>
            <n-card>
              <n-statistic label="每日接收推荐" :value="stats.dailyTotal">
                <template #prefix>✨</template>
                <template #suffix>篇</template>
              </n-statistic>
            </n-card>
          </n-grid-item>

          <n-grid-item>
            <n-card>
              <n-statistic label="LLM 每日预算" :value="stats.dailyBudget" :precision="2">
                <template #prefix>¥</template>
              </n-statistic>
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- Detailed Status Sections -->
        <n-grid cols="1 s:1 m:2 l:2" responsive="screen" :x-gap="16" :y-gap="16">
          <n-grid-item>
            <n-card title="🧠 推荐引擎个性化状态" bordered>
              <n-space vertical size="medium">
                <div class="info-row">
                  <span class="info-label">冷启动判定:</span>
                  <span>
                    <n-tag v-if="stats.totalPapers === 0" type="warning">等待数据抓取</n-tag>
                    <n-tag v-else type="success">就绪</n-tag>
                  </span>
                </div>
                
                <div class="info-row">
                  <span class="info-label">匹配模式门槛:</span>
                  <div style="font-size: 13px; color: #475569;">
                    <div>• 质心匹配: &ge; {{ stats.gateCentroid }} 个感兴趣标记</div>
                    <div>• 分类模型: &ge; {{ stats.gateModel }} 个感兴趣 + &ge; {{ stats.gateModel }} 个不感兴趣标记</div>
                  </div>
                </div>

                <div class="info-row" style="margin-top: 8px;">
                  <div style="font-size: 12px; color: #64748b; line-height: 1.5;">
                    提示: 在今日推荐页面或论文总览中标记论文为“感兴趣”或“不感兴趣”后，推荐引擎将渐进式地生成您的个人偏好特征，并最终建立个性化双分类预测模型。
                  </div>
                </div>
              </n-space>
            </n-card>
          </n-grid-item>

          <n-grid-item>
            <n-card title="⚙️ 快捷导航" bordered>
              <n-grid cols="2" :x-gap="12" :y-gap="12">
                <n-grid-item>
                  <n-button block type="primary" secondary @click="goTo('/digest')">
                    ✨ 今日推荐
                  </n-button>
                </n-grid-item>
                <n-grid-item>
                  <n-button block type="info" secondary @click="goTo('/papers')">
                    📄 论文总览
                  </n-button>
                </n-grid-item>
                <n-grid-item>
                  <n-button block type="warning" secondary @click="goTo('/keywords')">
                    🔑 关键词库
                  </n-button>
                </n-grid-item>
                <n-grid-item>
                  <n-button block type="success" secondary @click="goTo('/settings')">
                    ⚙️ 系统设置
                  </n-button>
                </n-grid-item>
              </n-grid>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-space>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { papersApi } from '../api/papers';
import { keywordsApi } from '../api/keywords';
import { settingsApi } from '../api/settings';

const router = useRouter();
const loading = ref(false);

const stats = ref({
  totalPapers: 0,
  totalKeywords: 0,
  dailyTotal: 6,
  dailyBudget: 0.50,
  gateCentroid: 1,
  gateModel: 20
});

onMounted(() => {
  fetchDashboardStats();
});

async function fetchDashboardStats() {
  loading.value = true;
  try {
    const [papersRes, keywordsRes, settingsRes] = await Promise.all([
      papersApi.list({ page: 1, size: 1 }),
      keywordsApi.list(),
      settingsApi.get()
    ]);
    
    stats.value.totalPapers = papersRes.data.total;
    stats.value.totalKeywords = keywordsRes.data.total;
    stats.value.dailyTotal = settingsRes.data.sources.daily_total;
    stats.value.dailyBudget = settingsRes.data.llm.daily_budget;
    stats.value.gateCentroid = settingsRes.data.recommender.min_pos_centroid ?? 1;
    stats.value.gateModel = settingsRes.data.recommender.min_pos_model ?? 20;
  } catch (err) {
    // Fail silently or handle gracefully
  } finally {
    loading.value = false;
  }
}

function goTo(path: string) {
  router.push(path);
}
</script>

<style scoped>
.dashboard-view {
  max-width: 1000px;
  margin: 0 auto;
}
.info-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-label {
  font-weight: 600;
  color: #334155;
  font-size: 14px;
}
</style>
