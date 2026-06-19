<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NButton, NSpace } from 'naive-ui'
import type { Keyword } from '@/types'

const props = defineProps<{
  show: boolean
  keyword?: Keyword | null
}>()

const emit = defineEmits<{
  close: []
  save: [data: Partial<Keyword>]
}>()

const form = ref({
  keyword: '',
  weight: 1.0,
  category: 'topic',
  aliases: [] as string[],
})

const categoryOptions = [
  { label: '主题', value: 'topic' },
  { label: '方法', value: 'method' },
  { label: '系统', value: 'system' },
]

const aliasInput = ref('')

watch(() => props.show, (v) => {
  if (v) {
    if (props.keyword) {
      form.value = {
        keyword: props.keyword.keyword,
        weight: props.keyword.weight,
        category: props.keyword.category,
        aliases: [...(props.keyword.aliases || [])],
      }
    } else {
      form.value = { keyword: '', weight: 1.0, category: 'topic', aliases: [] }
    }
    aliasInput.value = ''
  }
})

function addAlias() {
  const a = aliasInput.value.trim()
  if (a && !form.value.aliases.includes(a)) {
    form.value.aliases.push(a)
  }
  aliasInput.value = ''
}

function removeAlias(a: string) {
  form.value.aliases = form.value.aliases.filter(x => x !== a)
}

function handleSave() {
  emit('save', { ...form.value })
}
</script>

<template>
  <NModal :show="show" preset="card" :title="keyword ? '编辑关键词' : '添加关键词'" style="max-width: 480px;" @close="emit('close')">
    <NForm label-placement="left" label-width="80">
      <NFormItem label="关键词">
        <NInput v-model:value="form.keyword" placeholder="如: KV cache" />
      </NFormItem>
      <NFormItem label="权重">
        <NInputNumber v-model:value="form.weight" :min="-5" :max="5" :step="0.1" style="width: 100%;" />
      </NFormItem>
      <NFormItem label="分类">
        <NSelect v-model:value="form.category" :options="categoryOptions" />
      </NFormItem>
      <NFormItem label="别名">
        <NSpace vertical :size="6" style="width: 100%;">
          <NSpace :size="4">
            <NButton v-for="a in form.aliases" :key="a" size="tiny" @click="removeAlias(a)">{{ a }} ×</NButton>
          </NSpace>
          <NInput v-model:value="aliasInput" placeholder="输入别名后回车" @keyup.enter="addAlias" size="small" />
        </NSpace>
      </NFormItem>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" @click="handleSave" :disabled="!form.keyword.trim()">保存</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
