<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  document: { type: Object, required: true }
})

function nameToSlug(name) {
  return name.toLowerCase().trim().replace(/[^a-z0-9\s-]/g, '').replace(/[\s-]+/g, '-').replace(/^-|-$/g, '')
}

const activeTab = ref('scan')
const currentPageIdx = ref(0)
const scanEl = ref(null)
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })

const pages = computed(() => props.document.pages || [])
const currentPage = computed(() => pages.value[currentPageIdx.value] || {})

const formattedDate = computed(() => {
  if (!props.document.date) return ''
  const d = new Date(props.document.date)
  return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' })
})

const transformStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  cursor: scale.value > 1 ? 'grab' : 'zoom-in',
}))

const zoomLevels = [0.5, 0.75, 1, 1.5, 2, 3, 4]

function prevPage() {
  resetView()
  if (currentPageIdx.value > 0) currentPageIdx.value--
}

function nextPage() {
  resetView()
  if (currentPageIdx.value < pages.value.length - 1) currentPageIdx.value++
}

function handleImageError(e) {
  e.target.style.display = 'none'
  const placeholder = e.target.parentElement.querySelector('.scan-placeholder')
  if (placeholder) placeholder.style.display = 'flex'
}

function zoomIn() {
  const i = zoomLevels.findIndex(z => z > scale.value)
  if (i !== -1) scale.value = zoomLevels[i]
}

function zoomOut() {
  const i = zoomLevels.findIndex(z => z >= scale.value)
  if (i > 0) scale.value = zoomLevels[i - 1]
}

function zoomToFit() {
  scale.value = 1
  panX.value = 0
  panY.value = 0
}

function resetView() {
  scale.value = 1
  panX.value = 0
  panY.value = 0
}

function onWheel(e) {
  e.preventDefault()
  const delta = -Math.sign(e.deltaY)
  const rect = scanEl.value?.getBoundingClientRect()
  if (!rect) return
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const oldScale = scale.value
  const newScale = Math.min(4, Math.max(0.5, oldScale + delta * 0.25))
  scale.value = newScale
  panX.value = mx - (mx - panX.value) * (newScale / oldScale)
  panY.value = my - (my - panY.value) * (newScale / oldScale)
}

function onMouseDown(e) {
  if (scale.value <= 1) return
  isPanning.value = true
  panStart.value = { x: e.clientX - panX.value, y: e.clientY - panY.value }
  if (scanEl.value) scanEl.value.style.cursor = 'grabbing'
}

function onMouseMove(e) {
  if (!isPanning.value) return
  panX.value = e.clientX - panStart.value.x
  panY.value = e.clientY - panStart.value.y
}

function onMouseUp() {
  isPanning.value = false
  if (scanEl.value) scanEl.value.style.cursor = scale.value > 1 ? 'grab' : 'zoom-in'
}

function onClick(e) {
  if (isPanning.value) return
  onWheel({ ...e, deltaY: -150, preventDefault: () => {} })
}

onMounted(() => {
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('mousemove', onMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('mousemove', onMouseMove)
})
</script>

<template>
  <div class="document-dual-view" :class="['epoch-' + (document.epoch || '30er')]">
    <header class="document-header">
      <div class="document-meta">
        <EpochBadge :epoch="document.epoch" />
        <h1 class="document-title">{{ document.title }}</h1>
        <p class="document-date">{{ formattedDate }}</p>
        <div class="document-tags">
          <span v-if="document.document_type" class="tag">{{ document.document_type }}</span>
          <span v-if="document.topic" class="tag">{{ document.topic }}</span>
          <span v-if="document.place" class="tag">{{ document.place }}</span>
        </div>
      </div>
    </header>

    <div v-if="document.summary" class="document-summary">
      <p>{{ document.summary }}</p>
    </div>

    <div class="dual-container">
      <div class="dual-tabs" role="tablist">
        <button role="tab" id="tab-scan" :aria-selected="activeTab === 'scan'"
          class="tab-btn" :class="{ active: activeTab === 'scan' }"
          @click="activeTab = 'scan'">Scan</button>
        <button role="tab" id="tab-transcription" :aria-selected="activeTab === 'transcription'"
          class="tab-btn" :class="{ active: activeTab === 'transcription' }"
          @click="activeTab = 'transcription'">Transkription</button>
        <button v-if="document.persons?.length" role="tab" id="tab-persons"
          :aria-selected="activeTab === 'persons'"
          class="tab-btn" :class="{ active: activeTab === 'persons' }"
          @click="activeTab = 'persons'">Personen</button>
      </div>

      <div class="dual-columns">
        <div class="column column-scan">
          <div v-if="pages.length > 1" class="page-nav">
            <button class="page-nav-btn" :disabled="currentPageIdx === 0" @click="prevPage">&larr; Vorherige</button>
            <span class="page-nav-label">Seite {{ currentPageIdx + 1 }} / {{ pages.length }}</span>
            <button class="page-nav-btn" :disabled="currentPageIdx >= pages.length - 1" @click="nextPage">Nächste &rarr;</button>
          </div>
          <div class="scan-toolbar">
            <button class="toolbar-btn" title="Vergrößern" @click="zoomIn" :disabled="scale >= 4">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            </button>
            <span class="toolbar-label">{{ Math.round(scale * 100) }}%</span>
            <button class="toolbar-btn" title="Verkleinern" @click="zoomOut" :disabled="scale <= 0.5">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/></svg>
            </button>
            <button class="toolbar-btn" title="An Fenster anpassen" @click="zoomToFit">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
            </button>
          </div>
          <div class="scan-wrapper" ref="scanEl" @wheel.prevent="onWheel" @mousedown.prevent="onMouseDown" @click="onClick">
            <img v-if="currentPage.image_url" :src="currentPage.image_url"
              :alt="'Scan Seite ' + (currentPage.page_number || currentPageIdx + 1)"
              class="scan-image" :style="transformStyle"
              @error="handleImageError" draggable="false" />
            <div v-else class="scan-placeholder">
              <p>Scan nicht verfügbar</p>
            </div>
          </div>
        </div>

        <div class="column column-transcription">
          <div v-if="!document.transcription" class="transcription-empty">
            <p>Keine Transkription verfügbar.</p>
          </div>
          <div v-else class="transcription-wrapper">
            <p class="transcription-text">{{ document.transcription }}</p>
          </div>
        </div>
      </div>

      <div v-if="document.persons?.length" class="column column-persons">
        <h3 class="persons-title">Erwähnte Personen</h3>
        <ul class="persons-list">
          <li v-for="p in document.persons" :key="p.name" class="person-item">
            <RouterLink :to="'/person/' + nameToSlug(p.name)" class="person-link">
              {{ p.name }}
            </RouterLink>
            <span v-if="p.role" class="person-role">{{ p.role }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.document-dual-view {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-l);
}

.document-header {
  margin-bottom: var(--space-l);
}

.document-title {
  font-family: var(--font-serif);
  font-size: 2rem;
  margin: var(--space-s) 0;
  line-height: 1.2;
}

.document-date {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-s);
}

.document-tags {
  display: flex;
  gap: var(--space-s);
  flex-wrap: wrap;
}

.tag {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  padding: 2px var(--space-s);
  background: var(--color-epoch-badge);
  border-radius: 4px;
  color: var(--color-text-secondary);
}

.document-summary {
  font-family: var(--font-serif);
  font-size: 1.0625rem;
  line-height: 1.6;
  color: var(--color-text-primary);
  padding: var(--space-l);
  background: var(--color-surface);
  border-radius: 8px;
  margin-bottom: var(--space-l);
  border: 1px solid var(--color-border);
}

.dual-tabs {
  display: none;
  margin-bottom: var(--space-m);
}

.tab-btn {
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  padding: var(--space-s) var(--space-m);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  cursor: pointer;
}

.tab-btn:first-child { border-radius: 4px 0 0 4px; border-right: none; }
.tab-btn:last-child { border-radius: 0 4px 4px 0; }

.tab-btn.active {
  background: var(--color-epoch-primary);
  color: var(--color-surface);
  border-color: var(--color-epoch-primary);
}

.dual-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-l);
}

.column {
  background: var(--color-surface);
  border-radius: 8px;
  padding: var(--space-l);
  box-shadow: 0 4px 24px rgba(28, 25, 23, 0.08);
}

.page-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-m);
}

.page-nav-btn {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-epoch-primary);
  background: none;
  border: 1px solid var(--color-border);
  padding: var(--space-xs) var(--space-s);
  border-radius: 4px;
  cursor: pointer;
}

.page-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-nav-btn:hover:not(:disabled) {
  background: var(--color-epoch-primary);
  color: var(--color-surface);
}

.page-nav-label {
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}

.scan-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  margin-bottom: var(--space-s);
}

.toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--color-epoch-primary);
  color: var(--color-surface);
  border-color: var(--color-epoch-primary);
}

.toolbar-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.toolbar-label {
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  min-width: 40px;
  text-align: center;
}

.scan-wrapper {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E8E4DB;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  user-select: none;
}

.scan-image {
  max-width: 100%;
  max-height: 600px;
  object-fit: contain;
  transition: transform 100ms ease-out;
  transform-origin: 0 0;
  will-change: transform;
  pointer-events: none;
}

.scan-placeholder {
  font-family: var(--font-sans);
  color: var(--color-stub);
  padding: var(--space-xl);
}

.transcription-wrapper {
  min-height: 400px;
  max-height: 700px;
  overflow-y: auto;
}

.transcription-text {
  font-family: var(--font-serif);
  font-size: 1rem;
  line-height: 1.75;
  color: var(--color-text-primary);
  white-space: pre-wrap;
}

.transcription-empty {
  font-family: var(--font-sans);
  color: var(--color-stub);
  padding: var(--space-xl);
  text-align: center;
}

.column-persons {
  margin-top: var(--space-l);
}

.persons-title {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  font-weight: 700;
  margin-bottom: var(--space-m);
}

.persons-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-s);
}

.person-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-s);
  background: var(--color-bg);
  border-radius: 4px;
}

.person-link {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-epoch-primary);
  text-decoration: none;
  font-weight: 600;
}

.person-link:hover {
  text-decoration: underline;
}

.person-role {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-stub);
}

@media (max-width: 767px) {
  .dual-tabs {
    display: flex;
  }

  .dual-columns {
    display: none;
  }

  .dual-columns.dual-tabs-active {
    display: grid;
    grid-template-columns: 1fr;
  }

  .column-persons {
    display: none;
  }
}
</style>
