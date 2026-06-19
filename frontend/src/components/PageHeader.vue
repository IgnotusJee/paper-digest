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
  margin-bottom: 28px;
  gap: 16px;
  flex-wrap: wrap;
}

.header-title {
  font-size: 24px;
  font-weight: 800;
  color: #111827;
  margin: 0;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.header-desc {
  font-size: 14px;
  color: #9ca3af;
  margin: 6px 0 0;
  font-weight: 400;
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
