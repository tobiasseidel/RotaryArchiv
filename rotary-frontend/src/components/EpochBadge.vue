<script setup>
defineProps({
  epoch: {
    type: String,
    required: true,
    validator: (value) => ['30er', '90er'].includes(value)
  }
})

const epochLabels = {
  '30er': 'Die 30er',
  '90er': 'Die 90er'
}
</script>

<template>
  <span class="epoch-badge">{{ epochLabels[epoch] }}</span>
</template>

<style scoped>
.epoch-badge {
  display: inline-block;
  background: var(--color-epoch-badge);
  color: var(--color-epoch-primary);
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
