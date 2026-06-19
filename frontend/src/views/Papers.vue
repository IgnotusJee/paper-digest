<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NSelect, NPagination, NSpin } from 'naive-ui'
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
    <PageHeader title="论文库" description="浏览所有已入库论文">
      <template #actions>
        <span class="total-badge">共 {{ total }} 篇</span>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <NSelect v-model:value="bucket" :options="bucketOptions" placeholder="来源" clearable style="width: 140px;" />
      <NSelect v-model:value="sort" :options="sortOptions" style="width: 140px;" />
      <NSelect v-model:value="order" :options="orderOptions" style="width: 100px;" />
    </div>

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
.total-badge {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 14px;
  border-radius: 8px;
  background: #f3f4f6;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #f0f0f0;
  margin-bottom: 20px;
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
</style>
