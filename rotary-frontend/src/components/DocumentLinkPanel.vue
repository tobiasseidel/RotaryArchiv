<script setup>
defineProps({
  documentId: {
    type: [Number, String],
    required: true
  },
  label: {
    type: String,
    required: true
  }
})
</script>

<template>
  <RouterLink :to="`/dokument/${documentId}`" class="document-link-panel">
    <span class="arrow">→</span>
    <span class="label">{{ label }}</span>
  </RouterLink>
</template>

<style scoped>
.document-link-panel {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  border-left: 3px solid var(--color-epoch-accent);
  padding-left: var(--space-s);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.document-link-panel:hover {
  color: var(--color-epoch-primary);
}

.arrow {
  font-weight: 600;
}
</style>
