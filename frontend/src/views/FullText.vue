<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, NButton, NIcon, NSpin, NAlert } from 'naive-ui'
import { ArrowBackOutline, DocumentOutline, LanguageOutline } from '@vicons/ionicons5'
import * as papersApi from '@/api/papers'

const route = useRoute()
const router = useRouter()
const msg = useMessage()

const paperId = computed(() => Number(route.params.id))
const pdfUrl = ref<string | null>(null)
const fulltextCn = ref<string | null>(null)
const loading = ref(true)
const translating = ref(false)
const error = ref<string | null>(null)

async function loadFullText() {
  loading.value = true
  error.value = null
  try {
    const { data } = await papersApi.getFullText(paperId.value)
    pdfUrl.value = data.pdf_url
    fulltextCn.value = data.fulltext_cn
  } catch {
    error.value = '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleTranslate() {
  translating.value = true
  error.value = null
  try {
    const { data } = await papersApi.translateFullText(paperId.value)
    fulltextCn.value = data.fulltext_cn
    if (data.cached) {
      msg.info('已加载缓存翻译')
    } else {
      msg.success('翻译完成')
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '翻译失败，请稍后重试'
  } finally {
    translating.value = false
  }
}

onMounted(loadFullText)
</script>

<template>
  <div class="fulltext-page">
    <div class="fulltext-toolbar">
      <NButton quaternary @click="router.back()" size="small">
        <template #icon><NIcon :component="ArrowBackOutline" /></template>
        返回
      </NButton>
      <span class="toolbar-title">全文阅读</span>
      <NButton
        v-if="!fulltextCn"
        type="primary"
        :loading="translating"
        :disabled="!pdfUrl"
        @click="handleTranslate"
        size="small"
      >
        <template #icon><NIcon :component="LanguageOutline" /></template>
        {{ translating ? '翻译中...' : '翻译全文' }}
      </NButton>
      <NButton
        v-else
        quaternary
        type="primary"
        @click="handleTranslate"
        size="small"
      >
        <template #icon><NIcon :component="LanguageOutline" /></template>
        重新翻译
      </NButton>
    </div>

    <NAlert v-if="error" type="error" closable @close="error = null" class="fulltext-error">
      {{ error }}
    </NAlert>

    <div v-if="loading" class="fulltext-loading">
      <NSpin size="large" />
    </div>

    <div v-else class="fulltext-split">
      <div class="fulltext-panel fulltext-left">
        <div class="panel-header">
          <NIcon :component="DocumentOutline" :size="14" />
          <span>原文 PDF</span>
        </div>
        <div class="panel-body pdf-container">
          <iframe
            v-if="pdfUrl"
            :src="pdfUrl"
            class="pdf-iframe"
            title="PDF Viewer"
          />
          <div v-else class="no-pdf">无 PDF 链接</div>
        </div>
      </div>

      <div class="fulltext-divider" />

      <div class="fulltext-panel fulltext-right">
        <div class="panel-header">
          <NIcon :component="LanguageOutline" :size="14" />
          <span>中文翻译</span>
        </div>
        <div class="panel-body">
          <div v-if="translating" class="translating-state">
            <NSpin size="medium" />
            <p>正在翻译全文，请稍候...</p>
          </div>
          <div v-else-if="fulltextCn" class="translated-text" v-html="formatText(fulltextCn)" />
          <div v-else class="no-translation">
            <p>尚未翻译</p>
            <p class="hint">点击顶部「翻译全文」按钮开始</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
function formatText(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^## (.+)$/gm, '<h3 class="section-heading">$1</h3>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
}
</script>

<style scoped>
.fulltext-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  overflow: hidden;
}

.fulltext-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
  flex-shrink: 0;
}

.toolbar-title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.fulltext-error {
  margin: 0 20px;
  flex-shrink: 0;
}

.fulltext-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
}

.fulltext-split {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.fulltext-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.fulltext-left {
  flex: 1;
}

.fulltext-right {
  flex: 1;
}

.fulltext-divider {
  width: 1px;
  background: #e5e7eb;
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #f3f4f6;
  background: #fafbfc;
  flex-shrink: 0;
}

.panel-body {
  flex: 1;
  overflow: auto;
}

.pdf-container {
  background: #525659;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.no-pdf {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #9ca3af;
  font-size: 14px;
}

.translating-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: #6b7280;
}

.translating-state p {
  margin: 0;
  font-size: 14px;
}

.translated-text {
  padding: 20px 24px;
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
}

.translated-text :deep(p) {
  margin: 0 0 12px;
}

.translated-text :deep(.section-heading) {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 24px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e5e7eb;
}

.no-translation {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9ca3af;
}

.no-translation p {
  margin: 0;
  font-size: 14px;
}

.no-translation .hint {
  margin-top: 4px;
  font-size: 12px;
}
</style>
