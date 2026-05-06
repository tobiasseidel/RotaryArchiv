<script setup>
import { useEpochStore } from '@/stores/epoch'
import AppShell from '@/components/AppShell.vue'

const epochStore = useEpochStore()
</script>

<template>
  <AppShell :class="epochStore.epochClass">
    <RouterView />
  </AppShell>
</template>
