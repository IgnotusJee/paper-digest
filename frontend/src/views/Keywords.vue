<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NDataTable, NButton, NSpace, NIcon, NPopconfirm, NSelect, NCard, NTag } from 'naive-ui'
import { AddOutline, TrashOutline, CreateOutline, GitNetworkOutline } from '@vicons/ionicons5'
import PageHeader from '@/components/PageHeader.vue'
import KeywordModal from '@/components/KeywordModal.vue'
import * as keywordsApi from '@/api/keywords'
import type { Keyword } from '@/types'

const msg = useMessage()
const loading = ref(true)
const keywords = ref<Keyword[]>([])
const categoryFilter = ref<string | null>(null)
const showModal = ref(false)
const editingKeyword = ref<Keyword | null>(null)

const categoryOptions = [
  { label: '全部分类', value: '' },
  { label: '主题', value: 'topic' },
  { label: '方法', value: 'method' },
  { label: '系统', value: 'system' },
]

const columns = [
  { title: '关键词', key: 'keyword', ellipsis: { tooltip: true } },
  {
    title: '权重',
    key: 'weight',
    width: 100,
    render: (row: Keyword) => row.weight.toFixed(1),
  },
  { title: '分类', key: 'category', width: 80 },
  {
    title: '别名',
    key: 'aliases',
    ellipsis: { tooltip: true },
    render: (row: Keyword) => row.aliases?.join(', ') || '-',
  },
  { title: '来源', key: 'source', width: 80 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render(row: any) {
      return h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { text: true, size: 'small', onClick: () => openEdit(row) }, {
            icon: () => h(NIcon, { component: CreateOutline }),
          }),
          h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
            trigger: () => h(NButton, { text: true, size: 'small', type: 'error' }, {
              icon: () => h(NIcon, { component: TrashOutline }),
            }),
            default: () => '确认删除？',
          }),
        ],
      })
    },
  },
]

async function fetchKeywords() {
  loading.value = true
  try {
    const { data } = await keywordsApi.listKeywords(categoryFilter.value || undefined)
    keywords.value = data.items
  } catch {
    msg.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editingKeyword.value = null
  showModal.value = true
}

function openEdit(kw: Keyword) {
  editingKeyword.value = kw
  showModal.value = true
}

async function handleSave(data: Partial<Keyword>) {
  try {
    if (editingKeyword.value) {
      await keywordsApi.updateKeyword(editingKeyword.value.id, data)
      msg.success('已更新')
    } else {
      await keywordsApi.createKeyword(data)
      msg.success('已添加')
    }
    showModal.value = false
    fetchKeywords()
  } catch (err: any) {
    msg.error(err.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(id: number) {
  try {
    await keywordsApi.deleteKeyword(id)
    msg.success('已删除')
    fetchKeywords()
  } catch {
    msg.error('删除失败')
  }
}

async function handleLoadPreset() {
  try {
    const { data } = await keywordsApi.loadPreset('llm_infra')
    msg.success(`已加载预设：新增 ${data.loaded} 条，跳过 ${data.skipped} 条`)
    fetchKeywords()
  } catch (err: any) {
    msg.error(err.response?.data?.detail || '加载预设失败')
  }
}

onMounted(fetchKeywords)
</script>

<template>
  <div>
    <PageHeader title="关键词" description="维护推荐系统的主题词、方法词和系统词，直接影响召回与排序。">
      <template #actions>
        <NSpace>
          <NButton @click="handleLoadPreset" secondary>加载预设</NButton>
          <NButton type="primary" @click="openAdd">
            <template #icon><NIcon :component="AddOutline" /></template>
            添加关键词
          </NButton>
        </NSpace>
      </template>
    </PageHeader>

    <NCard class="keywords-card" :bordered="false">
      <div class="keywords-head">
        <div class="keywords-title-group">
          <div class="keywords-icon">
            <NIcon :size="18"><GitNetworkOutline /></NIcon>
          </div>
          <div>
            <h3 class="keywords-title">关键词字典</h3>
            <p class="keywords-copy">在这里维护召回词库和人工权重。</p>
          </div>
        </div>
        <NTag round :bordered="false" class="keywords-meta">{{ keywords.length }} 条记录</NTag>
      </div>

      <div class="keywords-filter">
        <NSelect
          v-model:value="categoryFilter"
          :options="categoryOptions"
          placeholder="筛选分类"
          clearable
          class="keywords-select"
          @update:value="fetchKeywords"
        />
      </div>

      <NDataTable
        :columns="columns"
        :data="keywords"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
      />
    </NCard>

    <KeywordModal
      :show="showModal"
      :keyword="editingKeyword"
      @close="showModal = false"
      @save="handleSave"
    />
  </div>
</template>

<style scoped>
.keywords-card {
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.keywords-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.keywords-title-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.keywords-icon {
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

.keywords-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.keywords-copy {
  margin: 4px 0 0;
  font-size: 13px;
  color: #64748b;
}

.keywords-meta {
  background: #f8fafc !important;
  color: #475569 !important;
  border: 1px solid #e2e8f0;
}

.keywords-filter {
  margin-bottom: 16px;
}

.keywords-select {
  width: 180px;
}

@media (max-width: 768px) {
  .keywords-head {
    flex-direction: column;
  }

  .keywords-select {
    width: 100%;
  }
}
</style>
