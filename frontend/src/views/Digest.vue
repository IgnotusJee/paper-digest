<template>
  <div class="digest-view">
    <div class="header-row">
      <div class="title-section">
        <h2>{{ selectedDate }} 日报推送</h2>
        <n-space style="margin-top: 4px;">
          <n-tag v-if="digestData?.degraded" type="warning" size="small">
            ⚠️ 排序降级 (未通过 LLM 精排)
          </n-tag>
          <n-tag :type="statusType" size="small">
            {{ statusLabel }}
          </n-tag>
        </n-space>
      </div>
      <div class="date-picker-section">
        <n-date-picker
          v-model:formatted-value="selectedDate"
          value-format="yyyy-MM-dd"
          type="date"
          :is-date-disabled="disableFutureDates"
          @update:value="handleDateChange"
        />
      </div>
    </div>

    <n-spin :show="loading">
      <div v-if="error" class="error-container">
        <n-result status="404" title="暂无推荐日报" description="该日期没有推送记录，或者抓取任务尚未运行">
          <template #footer>
            <n-button @click="loadToday">加载今日日报</n-button>
          </template>
        </n-result>
      </div>

      <div v-else-if="papers.length === 0" class="empty-container">
        <n-empty description="今日日报暂无论文推选" />
      </div>

      <div v-else class="content-container">
        <!-- Grid layout grouped by bucket -->
        <n-grid cols="1 s:1 m:2 l:2" responsive="screen" :x-gap="16" :y-gap="16">
          <n-grid-item>
            <n-card title="🏛️ 期刊会议推荐 (Venue Bucket)" class="bucket-column" header-style="background-color: #eff6ff; border-radius: 8px 8px 0 0;" bordered>
              <div v-if="venuePapers.length === 0" class="bucket-empty">
                无期刊会议录用推荐 (可能由于 quota=0 或筛选供给不足)
              </div>
              <div v-else class="papers-list">
                <paper-card
                  v-for="paper in venuePapers"
                  :key="paper.id"
                  :paper="paper"
                  @tag-updated="handleTagUpdated"
                />
              </div>
            </n-card>
          </n-grid-item>

          <n-grid-item>
            <n-card title="⚛️ arXiv 预印本推荐 (arXiv Bucket)" class="bucket-column" header-style="background-color: #f8fafc; border-radius: 8px 8px 0 0;" bordered>
              <div v-if="arxivPapers.length === 0" class="bucket-empty">
                无 arXiv 预印本推送 (可能由于 quota=0 或筛选供给不足)
              </div>
              <div v-else class="papers-list">
                <paper-card
                  v-for="paper in arxivPapers"
                  :key="paper.id"
                  :paper="paper"
                  @tag-updated="handleTagUpdated"
                />
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { digestApi } from '../api/digest';
import type { DigestHistory, Paper } from '../types';
import PaperCard from '../components/PaperCard.vue';
import { useMessage } from 'naive-ui';

const loading = ref(false);
const error = ref(false);
const selectedDate = ref<string>('');
const digestData = ref<DigestHistory | null>(null);
const message = useMessage();

const papers = computed(() => {
  return (digestData.value?.papers as Paper[]) || [];
});

const venuePapers = computed(() => {
  return papers.value.filter(p => p.bucket === 'venue');
});

const arxivPapers = computed(() => {
  return papers.value.filter(p => p.bucket === 'arxiv');
});

const statusType = computed(() => {
  const status = digestData.value?.status;
  if (status === 'sent') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'degraded') return 'warning';
  return 'default';
});

const statusLabel = computed(() => {
  const status = digestData.value?.status;
  if (status === 'sent') return '推送成功';
  if (status === 'failed') return '推送失败';
  if (status === 'degraded') return '降级推送';
  return status || '未知状态';
});

// Format today's date as YYYY-MM-DD local time
function getLocalDateString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

onMounted(() => {
  selectedDate.value = getLocalDateString();
  fetchDigest();
});

function disableFutureDates(ts: number) {
  return ts > Date.now();
}

async function fetchDigest() {
  if (!selectedDate.value) return;
  loading.value = true;
  error.value = false;
  try {
    const res = await digestApi.getByDate(selectedDate.value);
    digestData.value = res.data;
  } catch (err: any) {
    digestData.value = null;
    error.value = true;
    if (err.response && err.response.status !== 404) {
      message.error('获取日报失败: ' + (err.response.data?.detail || err.message));
    }
  } finally {
    loading.value = false;
  }
}

function handleDateChange() {
  fetchDigest();
}

function loadToday() {
  selectedDate.value = getLocalDateString();
  fetchDigest();
}

function handleTagUpdated(paperId: number, tagType: string | null) {
  // Update state locally inside the papers list
  if (digestData.value && digestData.value.papers) {
    const paper = digestData.value.papers.find(p => p.id === paperId);
    if (paper) {
      paper.tag_type = tagType as any;
    }
  }
}
</script>

<style scoped>
.digest-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.title-section h2 {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
}
.bucket-column {
  min-height: 500px;
  height: 100%;
}
.bucket-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  color: #94a3b8;
  font-size: 14px;
  text-align: center;
  border: 1px dashed #e2e8f0;
  border-radius: 8px;
}
.papers-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.error-container, .empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
</style>
