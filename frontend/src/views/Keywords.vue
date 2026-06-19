<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NDataTable, NButton, NSpace, NIcon, NPopconfirm, NSelect } from 'naive-ui'
import { AddOutline, TrashOutline, CreateOutline } from '@vicons/ionicons5'
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
    <PageHeader title="关键词" description="管理推荐系统的关键词权重">
      <template #actions>
        <NSpace>
          <NButton @click="handleLoadPreset" secondary round>加载预设</NButton>
          <NButton type="primary" @click="openAdd" round>
            <template #icon><NIcon :component="AddOutline" /></template>
            添加关键词
          </NButton>
        </NSpace>
      </template>
    </PageHeader>

    <div class="keywords-card">
      <div class="keywords-filter">
        <NSelect v-model:value="categoryFilter" :options="categoryOptions" placeholder="筛选分类" clearable style="width: 160px;" @update:value="fetchKeywords" />
      </div>

      <NDataTable
        :columns="columns"
        :data="keywords"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
      />
    </div>

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
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  border: 1px solid #f0f0f0;
}

.keywords-filter {
  margin-bottom: 16px;
}
</style>
