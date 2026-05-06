<script setup>
defineProps({
  epoch: {
    type: String,
    required: true,
    validator: (value) => ['30er', '90er'].includes(value)
  }
})
</script>

<template>
  <span class="epoch-badge" :class="'epoch-' + epoch">
    <span class="epoch-icon" aria-hidden="true">{{ epoch === '30er' ? '▪' : '◦' }}</span>
    Die {{ epoch }}
  </span>
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

.epoch-icon {
  margin-right: 4px;
  font-size: 0.6rem;
  vertical-align: middle;
}
</style>
