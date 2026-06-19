<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()

defineSlots<{
  default(): any
  actions(): any
}>()
</script>

<template>
  <div class="page-header">
    <div class="header-text">
      <h1 class="header-title">{{ title }}</h1>
      <p v-if="description" class="header-desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.header-title {
  font-size: 26px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
  line-height: 1.15;
}

.header-desc {
  font-size: 14px;
  color: #64748b;
  margin: 8px 0 0;
  font-weight: 400;
  max-width: 64ch;
}

.header-actions {
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .header-title {
    font-size: 20px;
  }

  .page-header {
    margin-bottom: 20px;
  }
}
</style>
