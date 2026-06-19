<template>
  <div class="papers-view">
    <!-- Filters & Settings -->
    <n-card class="filter-card" size="small" style="margin-bottom: 16px;">
      <n-space justify="space-between" align="center" wrap>
        <n-space align="center">
          <span>分桶过滤:</span>
          <n-select
            v-model:value="filterParams.bucket"
            :options="bucketOptions"
            placeholder="全部"
            clearable
            style="width: 150px;"
            @update:value="handleFilterChange"
          />
        </n-space>
        
        <n-space align="center">
          <span>排序字段:</span>
          <n-select
            v-model:value="filterParams.sort"
            :options="sortOptions"
            style="width: 150px;"
            @update:value="handleFilterChange"
          />
          <n-select
            v-model:value="filterParams.order"
            :options="orderOptions"
            style="width: 100px;"
            @update:value="handleFilterChange"
          />
        </n-space>
      </n-space>
    </n-card>

    <!-- Table -->
    <n-spin :show="loading">
      <n-card bordered>
        <div v-if="papers.length === 0" style="padding: 40px 0;">
          <n-empty description="没有找到论文" />
        </div>
        
        <div v-else>
          <n-list hoverable clickable>
            <n-list-item v-for="paper in papers" :key="paper.id" @click="viewDetail(paper.id)">
              <template #suffix>
                <div style="text-align: right; min-width: 100px;">
                  <div style="font-weight: bold; font-size: 15px; color: #0f172a;">
                    {{ paper.final_score.toFixed(2) }} 分
                  </div>
                  <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                    关键词: {{ paper.keyword_score.toFixed(2) }}
                  </div>
                </div>
              </template>
              
              <n-thing>
                <template #title>
                  <span style="font-weight: 600; color: #1e293b;">
                    {{ paper.summary_cn?.title_cn || paper.title }}
                  </span>
                </template>
                
                <template #description>
                  <span style="font-size: 13px; color: #64748b;">
                    {{ formatAuthors(paper.authors) }}
                  </span>
                </template>

                <div style="margin-top: 8px;">
                  <n-space size="small">
                    <n-tag :type="getBucketType(paper.bucket)" size="small">
                      {{ getBucketLabel(paper.bucket) }}
                    </n-tag>
                    <n-tag v-if="paper.venue" type="warning" size="small">
                      {{ paper.venue }}
                    </n-tag>
                    <n-tag v-else-if="paper.venue_hint" type="warning" size="small">
                      {{ paper.venue_hint }}
                    </n-tag>
                    <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">
                      收录于: {{ formatDate(paper.created_at) }}
                    </span>
                  </n-space>
                </div>
              </n-thing>
            </n-list-item>
          </n-list>

          <!-- Pagination -->
          <div class="pagination-row">
            <n-pagination
              v-model:page="filterParams.page"
              v-model:page-size="filterParams.size"
              :item-count="totalItems"
              :page-sizes="[10, 20, 50, 100]"
              show-size-picker
              style="margin-top: 20px; justify-content: flex-end;"
              @update:page="handlePageChange"
              @update:page-size="handlePageSizeChange"
            />
          </div>
        </div>
      </n-card>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import type { Paper } from '../types';
import { papersApi } from '../api/papers';
import type { ListPapersParams } from '../api/papers';
import { useMessage } from 'naive-ui';

const router = useRouter();
const message = useMessage();

const papers = ref<Paper[]>([]);
const totalItems = ref(0);
const loading = ref(false);

const filterParams = ref<Required<ListPapersParams>>({
  page: 1,
  size: 20,
  sort: 'created_at',
  order: 'desc',
  bucket: null
});

const bucketOptions = [
  { label: '全部分桶', value: null },
  { label: '期刊会议 (venue)', value: 'venue' },
  { label: 'arXiv 预印本 (arxiv)', value: 'arxiv' }
];

const sortOptions = [
  { label: '收录时间', value: 'created_at' },
  { label: '综合得分', value: 'final_score' },
  { label: '关键词打分', value: 'keyword_score' }
];

const orderOptions = [
  { label: '降序', value: 'desc' },
  { label: '升序', value: 'asc' }
];

onMounted(() => {
  fetchPapers();
});

async function fetchPapers() {
  loading.value = true;
  try {
    const res = await papersApi.list(filterParams.value);
    papers.value = res.data.items;
    totalItems.value = res.data.total;
  } catch (err) {
    message.error('获取论文列表失败');
  } finally {
    loading.value = false;
  }
}

function handleFilterChange() {
  filterParams.value.page = 1;
  fetchPapers();
}

function handlePageChange() {
  fetchPapers();
}

function handlePageSizeChange() {
  filterParams.value.page = 1;
  fetchPapers();
}

function viewDetail(id: number) {
  router.push(`/papers/${id}`);
}

function formatAuthors(authors: any): string {
  if (!authors) return '';
  if (Array.isArray(authors)) {
    return authors.join(', ');
  }
  try {
    const parsed = typeof authors === 'string' ? JSON.parse(authors) : authors;
    if (Array.isArray(parsed)) {
      return parsed.join(', ');
    }
  } catch (e) {}
  return String(authors);
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  return dateStr.split('T')[0];
}

function getBucketType(bucket: string | null) {
  if (bucket === 'venue') return 'info';
  if (bucket === 'arxiv') return 'default';
  return 'warning';
}

function getBucketLabel(bucket: string | null) {
  if (bucket === 'venue') return '期刊会议';
  if (bucket === 'arxiv') return 'arXiv';
  return '未归桶';
}
</script>

<style scoped>
.papers-view {
  display: flex;
  flex-direction: column;
}
.filter-card {
  border-radius: 8px;
}
.pagination-row {
  display: flex;
  justify-content: flex-end;
}
</style>
