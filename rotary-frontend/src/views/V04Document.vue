<script setup>
import { useRoute, RouterLink } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useEpochStore } from '@/stores/epoch'
import DocumentDualView from '@/components/DocumentDualView.vue'

const route = useRoute()
const { getDocument } = useApi()
const epochStore = useEpochStore()

const id = computed(() => parseInt(route.params.id))
const highlight = computed(() => route.query.highlight || null)
const document = ref(null)
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    loading.value = true
    const data = await getDocument(id.value)
    document.value = data
    if (data.epoch) {
      epochStore.setEpoch(data.epoch)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="view-document" :class="['epoch-' + (document?.epoch || '30er')]">
    <div v-if="loading" class="loading-state">
      <div class="skeleton-header"></div>
      <div class="skeleton-dual">
        <div class="skeleton-block"></div>
        <div class="skeleton-block"></div>
      </div>
    </div>

    <div v-else-if="error" class="error-state">
      <h1>Dokument nicht gefunden</h1>
      <p>Das gesuchte Dokument existiert nicht im RotaryArchiv.</p>
      <RouterLink to="/" class="back-link">← Zurück zur Startseite</RouterLink>
    </div>

    <DocumentDualView v-else :document="document" :highlight="highlight" />
  </div>
</template>

<style scoped>
.view-document {
  min-height: 50vh;
}

.loading-state {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-l);
}

.skeleton-header {
  height: 60px;
  width: 60%;
  background: linear-gradient(90deg, var(--color-bg) 25%, var(--color-surface) 50%, var(--color-bg) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
  margin-bottom: var(--space-l);
}

.skeleton-dual {
  display: flex;
  gap: var(--space-l);
}

.skeleton-block {
  flex: 1;
  height: 400px;
  background: linear-gradient(90deg, var(--color-bg) 25%, var(--color-surface) 50%, var(--color-bg) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.error-state {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-xl) var(--space-l);
  text-align: center;
}

.error-state h1 {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  margin-bottom: var(--space-m);
}

.error-state p {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-l);
}

.back-link {
  display: inline-block;
  color: var(--color-epoch-primary);
  text-decoration: none;
  font-family: var(--font-sans);
}

.back-link:hover {
  text-decoration: underline;
}
</style>
