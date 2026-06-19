<template>
  <div class="quota-editor">
    <n-space vertical size="large">
      <n-card v-for="bucket in buckets" :key="bucket.name" :title="bucket.name === 'venue' ? '期刊会议分桶 (venue)' : 'arXiv 预印本分桶 (arxiv)'" bordered>
        <template #header-extra>
          <n-switch v-model:value="bucket.enabled" />
        </template>
        
        <n-form label-placement="left" label-width="120px" :disabled="!bucket.enabled">
          <n-form-item label="推送配额 (quota)">
            <div style="width: 100%; display: flex; align-items: center; gap: 12px;">
              <n-slider v-model:value="bucket.quota" :min="0" :max="20" style="flex: 1;" />
              <n-input-number v-model:value="bucket.quota" size="small" :min="0" :max="20" style="width: 80px;" />
            </div>
          </n-form-item>

          <template v-if="bucket.name === 'venue'">
            <n-form-item label="包含 DBLP">
              <n-switch v-model:value="bucket.include_dblp" />
            </n-form-item>
            <n-form-item label="包含预印本指向">
              <n-switch v-model:value="bucket.include_venue_hint" />
            </n-form-item>
            <n-form-item label="目标期刊会议列表">
              <n-dynamic-tags v-model:value="bucket.venues" />
              <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                当 arXiv 论文备注包含以上关键字（如 OSDI、SOSP），且开启了“包含预印本指向”，将被归为此桶。
              </div>
            </n-form-item>
          </template>

          <template v-else-if="bucket.name === 'arxiv'">
            <n-form-item label="arXiv 分类">
              <n-dynamic-tags v-model:value="bucket.arxiv_categories" />
              <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                增量抓取的 arXiv 子类别名列表（如 cs.DC、cs.AR、cs.AI）。
              </div>
            </n-form-item>
          </template>
        </n-form>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import type { BucketConfig } from '../types';

const props = defineProps<{
  buckets: BucketConfig[];
}>();
</script>

<style scoped>
.quota-editor {
  width: 100%;
}
</style>
