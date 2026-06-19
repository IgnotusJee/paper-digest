<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NSelect, NPagination, NSpin, NCard, NTag, NIcon } from 'naive-ui'
import { DocumentTextOutline, FunnelOutline } from '@vicons/ionicons5'
import PageHeader from '@/components/PageHeader.vue'
import PaperCard from '@/components/PaperCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import * as papersApi from '@/api/papers'
import type { PaperListItem, TagType } from '@/types'

const router = useRouter()
const msg = useMessage()
const loading = ref(true)
const papers = ref<PaperListItem[]>([])
const total = ref(0)
const page = ref(1)
const pages = ref(1)

const bucket = ref<string | null>(null)
const sort = ref('created_at')
const order = ref('desc')

const bucketOptions = [
  { label: '全部来源', value: '' },
  { label: '顶会', value: 'venue' },
  { label: 'arXiv', value: 'arxiv' },
]

const sortOptions = [
  { label: '入库时间', value: 'created_at' },
  { label: '综合分数', value: 'final_score' },
  { label: '关键词分数', value: 'keyword_score' },
]

const orderOptions = [
  { label: '降序', value: 'desc' },
  { label: '升序', value: 'asc' },
]

const activeFilterCount = computed(() => {
  let count = 0
  if (bucket.value) count += 1
  if (sort.value !== 'created_at') count += 1
  if (order.value !== 'desc') count += 1
  return count
})

async function fetchPapers() {
  loading.value = true
  try {
    const { data } = await papersApi.listPapers({
      page: page.value,
      size: 20,
      sort: sort.value,
      order: order.value,
      bucket: bucket.value || undefined,
    })
    papers.value = data.items
    total.value = data.total
    pages.value = data.pages
  } catch {
    msg.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function handleTag(paperId: number, type: TagType) {
  try {
    await papersApi.addTag(paperId, type)
    msg.success('已标记')
  } catch {
    msg.error('标记失败')
  }
}

async function handleRemoveTag(paperId: number) {
  try {
    await papersApi.removeTag(paperId)
    msg.success('已取消')
  } catch {
    msg.error('取消失败')
  }
}

function goToDetail(paperId: number) {
  router.push(`/papers/${paperId}`)
}

watch([bucket, sort, order], () => {
  page.value = 1
  fetchPapers()
})

onMounted(fetchPapers)
</script>

<template>
  <div>
    <PageHeader title="论文库" description="浏览所有已入库论文，按来源和排序方式快速筛读。">
      <template #actions>
        <div class="header-metrics">
          <span class="total-badge">共 {{ total }} 篇</span>
          <NTag v-if="activeFilterCount" round :bordered="false" class="filter-tag">
            {{ activeFilterCount }} 个筛选条件
          </NTag>
        </div>
      </template>
    </PageHeader>

    <NCard class="filter-card" :bordered="false">
      <div class="filter-head">
        <div class="filter-title-group">
          <div class="filter-icon">
            <NIcon :size="18"><FunnelOutline /></NIcon>
          </div>
          <div>
            <h3 class="filter-title">筛选与排序</h3>
            <p class="filter-copy">按来源、时间和分数切换阅读顺序。</p>
          </div>
        </div>
        <div class="library-badge">
          <NIcon :size="16"><DocumentTextOutline /></NIcon>
          Research archive
        </div>
      </div>

      <div class="filter-bar">
        <NSelect v-model:value="bucket" :options="bucketOptions" placeholder="来源" clearable class="filter-select" />
        <NSelect v-model:value="sort" :options="sortOptions" class="filter-select" />
        <NSelect v-model:value="order" :options="orderOptions" class="filter-select filter-select-small" />
      </div>
    </NCard>

    <div v-if="loading" class="loading-state">
      <NSpin size="large" />
    </div>

    <template v-else>
      <div v-if="papers.length" class="paper-list">
        <PaperCard
          v-for="paper in papers"
          :key="paper.id"
          :paper="paper"
          @tag="handleTag"
          @remove="handleRemoveTag"
          @click="goToDetail"
        />
      </div>
      <EmptyState v-else description="暂无论文" />

      <div v-if="pages > 1" class="pagination-wrapper">
        <NPagination v-model:page="page" :page-count="pages" @update:page="fetchPapers" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.header-metrics {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.total-badge {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.filter-tag {
  background: #eff6ff !important;
  color: #1d4ed8 !important;
}

.filter-card {
  margin-bottom: 20px;
  border-radius: 12px !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
}

.filter-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.filter-title-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.filter-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eff6ff;
  color: #1d4ed8;
  flex-shrink: 0;
}

.filter-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.filter-copy {
  margin: 4px 0 0;
  font-size: 13px;
  color: #64748b;
}

.library-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 12px;
  white-space: nowrap;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select {
  width: 160px;
}

.filter-select-small {
  width: 120px;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}

.paper-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 28px;
}

@media (max-width: 768px) {
  .filter-head {
    flex-direction: column;
  }

  .filter-select,
  .filter-select-small {
    width: 100%;
  }
}
</style>
