<script setup>
import { useEpochStore } from '@/stores/epoch'

const epochStore = useEpochStore()
</script>

<template>
  <div id="app" :class="['app', epochStore.epochClass]">
    <RouterView />
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
}
</style>
