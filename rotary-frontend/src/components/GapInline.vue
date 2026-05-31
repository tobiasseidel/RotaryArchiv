<script setup>
defineProps({
  bboxId: {
    type: String,
    required: true
  },
  isSubmitted: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['gap-clicked'])
</script>

<template>
  <span
    class="gap-inline"
    :class="{ 'gap-submitted': isSubmitted }"
    :title="isSubmitted ? 'Beitrag eingereicht' : 'Unleserliche Stelle — klicken zum Mitmachen'"
    role="button"
    tabindex="0"
    :aria-label="isSubmitted ? 'Beitrag eingereicht' : 'Unleserliche Stelle — klicken zum Mitmachen'"
    @click="emit('gap-clicked', bboxId)"
    @keydown.enter="emit('gap-clicked', bboxId)"
  >
    <template v-if="isSubmitted">✓</template>
    <template v-else>░░░░░</template>
  </span>
</template>

<style scoped>
.gap-inline {
  display: inline-block;
  font-family: var(--font-sans);
  font-size: 0.875em;
  border-bottom: 1px dashed var(--color-stub);
  cursor: pointer;
  vertical-align: middle;
  transition: opacity var(--transition-fast);
  padding: 0 2px;
}

.gap-inline:hover {
  opacity: 0.7;
}

.gap-inline.gap-submitted {
  color: var(--color-success);
  border-bottom: none;
  cursor: default;
  background: rgba(59, 110, 74, 0.12);
  border-radius: 2px;
  padding: 2px 6px;
}

.gap-inline.gap-submitted:hover {
  opacity: 1;
}
</style>
