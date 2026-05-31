<script setup>
import { useRoute, RouterLink } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useEpochStore } from '@/stores/epoch'
import DocumentDualView from '@/components/DocumentDualView.vue'
import ContributionModalMini from '@/components/ContributionModalMini.vue'
import EpochBadge from '@/components/EpochBadge.vue'

const route = useRoute()
const { getDocument } = useApi()
const epochStore = useEpochStore()

const id = computed(() => parseInt(route.params.id))
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

const selectedBbox = ref(null)
const submittedBboxIds = ref([])
const toastVisible = ref(false)
const toastMessage = ref('')
let toastTimer = null

function handleGapClicked(bbox) {
  selectedBbox.value = bbox
}

function handleModalSubmit(bboxId, text) {
  console.log('Gap submitted:', { bboxId, text })
  submittedBboxIds.value = [...submittedBboxIds.value, bboxId]
  selectedBbox.value = null
  showToast('Danke für Ihren Beitrag!')
}

function handleModalClose() {
  selectedBbox.value = null
}

function showToast(message) {
  toastMessage.value = message
  toastVisible.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toastVisible.value = false
  }, 3000)
}
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

    <div v-else-if="document.stub" class="stub-state">
      <div class="stub-content">
        <EpochBadge :epoch="document.epoch || '90er'" />
        <h1 class="stub-title">
          {{ document.epoch === '30er' ? 'Protokoll der 30er' : 'Protokoll der 90er' }}
        </h1>
        <p class="stub-explanation">
          Dieses Protokoll ist noch nicht öffentlich einsehbar.
          Das RotaryArchiv befindet sich im Aufbau und sammelt Informationen über ehemalige Mitglieder.
        </p>
        <p class="stub-explanation">
          Um vollständigen Zugang zu erhalten, melden Sie sich als Mitglied an.
        </p>
        <a href="#" class="login-cta">Jetzt einloggen</a>
      </div>
    </div>

    <DocumentDualView
      v-else
      :document="document"
      :submitted-bbox-ids="submittedBboxIds"
      @gap-clicked="handleGapClicked"
    />

    <ContributionModalMini
      v-if="selectedBbox"
      :bbox="selectedBbox"
      @submit="handleModalSubmit"
      @close="handleModalClose"
    />

    <Teleport to="body">
      <div v-if="toastVisible" class="toast" role="status" aria-live="polite">
        {{ toastMessage }}
      </div>
    </Teleport>
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

.stub-state {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-xl) var(--space-l);
}

.stub-content {
  max-width: 600px;
  margin: 0 auto;
  text-align: center;
}

.stub-title {
  font-family: var(--font-serif);
  font-size: 2rem;
  margin: var(--space-m) 0;
  color: var(--color-text-secondary);
}

.stub-explanation {
  font-family: var(--font-sans);
  font-size: 1rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-m);
}

.login-cta {
  display: inline-block;
  background: var(--color-epoch-primary);
  color: var(--color-surface);
  padding: var(--space-m) var(--space-l);
  border-radius: 8px;
  text-decoration: none;
  font-family: var(--font-sans);
  font-weight: 600;
  margin-top: var(--space-m);
  transition: background var(--transition-fast);
}

.login-cta:hover {
  background: var(--color-epoch-accent);
}

.toast {
  position: fixed;
  bottom: var(--space-xl);
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-epoch-primary);
  color: var(--color-surface);
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  font-weight: 600;
  padding: var(--space-m) var(--space-l);
  border-radius: 8px;
  z-index: 300;
  box-shadow: 0 4px 24px rgba(28, 25, 23, 0.2);
  animation: toast-in 300ms ease-out;
  pointer-events: none;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}
</style>
