<template>
  <div class="keywords-view">
    <n-space vertical size="large">
      <!-- Create Keyword / Load Preset Actions -->
      <n-card title="⚙️ 快捷操作" size="small">
        <n-space justify="space-between" align="center" wrap>
          <n-button type="primary" @click="showAddModal = true">
            ＋ 新增关键词
          </n-button>
          
          <n-space align="center">
            <span>加载内置关键词包:</span>
            <n-button secondary type="info" :loading="presetLoading" @click="loadLLMInfraPreset">
              📚 导入 llm_infra (LLM基础设施)
            </n-button>
          </n-space>
        </n-space>
      </n-card>

      <!-- Keywords list card -->
      <n-card title="🔑 关键词库" bordered>
        <n-spin :show="loading">
          <div v-if="keywords.length === 0" style="padding: 40px 0; text-align: center;">
            <n-empty description="暂无关键词，请新增或导入预设" />
          </div>

          <div v-else>
            <n-table :single-line="false" striped>
              <thead>
                <tr>
                  <th>关键词 (Keyword)</th>
                  <th>别名 (Aliases)</th>
                  <th>类别 (Category)</th>
                  <th>权重 (Weight)</th>
                  <th>来源 (Source)</th>
                  <th style="width: 150px; text-align: center;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="kw in keywords" :key="kw.id">
                  <td><strong>{{ kw.keyword }}</strong></td>
                  <td>
                    <n-space size="small">
                      <n-tag v-for="alias in kw.aliases" :key="alias" size="small" :bordered="false">
                        {{ alias }}
                      </n-tag>
                      <span v-if="!kw.aliases || kw.aliases.length === 0" style="color: #cbd5e1; font-size: 12px;">无</span>
                    </n-space>
                  </td>
                  <td>
                    <n-tag :type="getCategoryType(kw.category)" size="small">
                      {{ getCategoryLabel(kw.category) }}
                    </n-tag>
                  </td>
                  <td>
                    <!-- Editable Weight -->
                    <n-input-number
                      v-model:value="kw.weight"
                      size="small"
                      style="width: 100px;"
                      :step="0.1"
                      @blur="updateKeywordWeight(kw)"
                    />
                  </td>
                  <td>
                    <n-tag size="small" :bordered="false">{{ kw.source }}</n-tag>
                  </td>
                  <td style="text-align: center;">
                    <n-space justify="center">
                      <n-button size="small" type="primary" secondary @click="openEditModal(kw)">
                        编辑
                      </n-button>
                      <n-popconfirm
                        @positive-click="deleteKeyword(kw.id)"
                        positive-text="确认"
                        negative-text="取消"
                      >
                        <template #trigger>
                          <n-button size="small" type="error" secondary>
                            删除
                          </n-button>
                        </template>
                        确认要删除这个关键词吗？这将影响后续的过滤打分。
                      </n-popconfirm>
                    </n-space>
                  </td>
                </tr>
              </tbody>
            </n-table>
          </div>
        </n-spin>
      </n-card>
    </n-space>

    <!-- Add/Edit Modal -->
    <n-modal v-model:show="showAddModal" preset="card" :title="editMode ? '编辑关键词' : '新增关键词'" style="max-width: 500px;" @after-leave="resetForm">
      <n-form ref="formRef" :model="formValue" :rules="rules" label-placement="left" label-width="100px">
        <n-form-item label="关键词" path="keyword">
          <n-input v-model:value="formValue.keyword" placeholder="例如: GPU, FlashAttention" :disabled="editMode" />
        </n-form-item>
        
        <n-form-item label="分类" path="category">
          <n-select v-model:value="formValue.category" :options="categoryOptions" />
        </n-form-item>
        
        <n-form-item label="匹配权重" path="weight">
          <n-input-number v-model:value="formValue.weight" :step="0.1" style="width: 100%;" />
          <template #feedback>
            正数表示感兴趣（加分），负数表示排斥（减分）
          </template>
        </n-form-item>
        
        <n-form-item label="别名列表" path="aliases">
          <n-dynamic-tags v-model:value="formValue.aliases" />
          <template #feedback>
            输入别名后按回车，它们将获得与主词同等的打分匹配权
          </template>
        </n-form-item>
      </n-form>
      
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" :loading="submitLoading" @click="submitForm">
            保存
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { Keyword } from '../types';
import { keywordsApi } from '../api/keywords';
import { useMessage } from 'naive-ui';
import type { FormInst } from 'naive-ui';

const keywords = ref<Keyword[]>([]);
const loading = ref(false);
const presetLoading = ref(false);
const showAddModal = ref(false);
const editMode = ref(false);
const submitLoading = ref(false);
const formRef = ref<FormInst | null>(null);
const editingKeywordId = ref<number | null>(null);

const formValue = ref({
  keyword: '',
  category: 'topic',
  weight: 1.0,
  aliases: [] as string[]
});

const rules = {
  keyword: {
    required: true,
    message: '请输入关键词',
    trigger: 'blur'
  },
  category: {
    required: true,
    message: '请选择分类',
    trigger: 'blur'
  }
};

const categoryOptions = [
  { label: '研究主题 (topic)', value: 'topic' },
  { label: '方法论 (method)', value: 'method' },
  { label: '系统架构 (system)', value: 'system' }
];

onMounted(() => {
  fetchKeywords();
});

async function fetchKeywords() {
  loading.value = true;
  try {
    const res = await keywordsApi.list();
    keywords.value = res.data.items;
  } catch (err) {
    message.error('获取关键词失败');
  } finally {
    loading.value = false;
  }
}

function getCategoryType(cat: string) {
  if (cat === 'topic') return 'info';
  if (cat === 'method') return 'success';
  if (cat === 'system') return 'warning';
  return 'default';
}

function getCategoryLabel(cat: string) {
  if (cat === 'topic') return '主题';
  if (cat === 'method') return '方法';
  if (cat === 'system') return '系统';
  return cat;
}

const message = useMessage();

async function updateKeywordWeight(kw: Keyword) {
  try {
    await keywordsApi.update(kw.id, { weight: kw.weight });
    message.success(`已更新权重 ${kw.keyword} -> ${kw.weight}`);
  } catch (e) {
    message.error('更新权重失败');
    fetchKeywords(); // Revert local state on error
  }
}

function openEditModal(kw: Keyword) {
  editMode.value = true;
  editingKeywordId.value = kw.id;
  formValue.value = {
    keyword: kw.keyword,
    category: kw.category,
    weight: kw.weight,
    aliases: kw.aliases ? [...kw.aliases] : []
  };
  showAddModal.value = true;
}

function resetForm() {
  editMode.value = false;
  editingKeywordId.value = null;
  formValue.value = {
    keyword: '',
    category: 'topic',
    weight: 1.0,
    aliases: []
  };
}

async function submitForm() {
  formRef.value?.validate(async (errors) => {
    if (errors) return;

    submitLoading.value = true;
    try {
      if (editMode.value && editingKeywordId.value) {
        await keywordsApi.update(editingKeywordId.value, {
          category: formValue.value.category,
          weight: formValue.value.weight,
          aliases: formValue.value.aliases
        });
        message.success('更新关键词成功');
      } else {
        await keywordsApi.create(
          formValue.value.keyword,
          formValue.value.weight,
          formValue.value.category,
          formValue.value.aliases.length > 0 ? formValue.value.aliases : null
        );
        message.success('新增关键词成功');
      }
      showAddModal.value = false;
      fetchKeywords();
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || '保存失败';
      message.error(errMsg);
    } finally {
      submitLoading.value = false;
    }
  });
}

async function deleteKeyword(id: number) {
  try {
    await keywordsApi.delete(id);
    message.success('删除成功');
    fetchKeywords();
  } catch (e) {
    message.error('删除失败');
  }
}

async function loadLLMInfraPreset() {
  presetLoading.value = true;
  try {
    const res = await keywordsApi.loadPreset('llm_infra');
    message.success(`预设导入成功: 新增 ${res.data.loaded} 个，跳过已存在词 ${res.data.skipped} 个`);
    fetchKeywords();
  } catch (err: any) {
    message.error('导入预设包失败: ' + (err.response?.data?.detail || err.message));
  } finally {
    presetLoading.value = false;
  }
}
</script>

<style scoped>
.keywords-view {
  max-width: 1000px;
  margin: 0 auto;
}
</style>
