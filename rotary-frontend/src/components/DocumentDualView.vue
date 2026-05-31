<script setup>
import { ref, computed } from 'vue'
import EpochBadge from '@/components/EpochBadge.vue'
import GapInline from '@/components/GapInline.vue'

const props = defineProps({
  document: {
    type: Object,
    required: true
  },
  submittedBboxIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['gap-clicked'])

const activeTab = ref('scan')
const imageZoomed = ref(false)

const page = computed(() => {
  return props.document.pages?.[0] || {}
})

const formattedDate = computed(() => {
  const d = new Date(props.document.date)
  return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' })
})

function parseTranscription(ocrText, bboxData) {
  if (!ocrText) return []

  const lowConfidenceGaps = (bboxData || []).filter(
    b => b.role === 'unreadable' || b.text === null
  )

  if (lowConfidenceGaps.length === 0) {
    return [{ type: 'text', content: ocrText, bboxId: null }]
  }

  const firstGap = lowConfidenceGaps[0]
  const segments = []
  const insertPosition = Math.floor(ocrText.length * 0.4)

  if (insertPosition > 0) {
    segments.push({ type: 'text', content: ocrText.substring(0, insertPosition), bboxId: null })
    segments.push({ type: 'gap', content: '░░░░░', bboxId: firstGap.id, bbox: firstGap })
    segments.push({ type: 'text', content: ocrText.substring(insertPosition), bboxId: null })
  } else {
    segments.push({ type: 'text', content: ocrText, bboxId: null })
  }

  return segments
}

const transcriptionSegments = computed(() => {
  return parseTranscription(page.value.ocr_text, props.document.bbox_data)
})

function handleImageError(e) {
  e.target.style.display = 'none'
  const placeholder = e.target.parentElement.querySelector('.scan-placeholder')
  if (placeholder) {
    placeholder.style.display = 'flex'
  }
}

function toggleZoom() {
  imageZoomed.value = !imageZoomed.value
}
</script>

<template>
  <div class="document-dual-view" :class="['epoch-' + (document.epoch || '30er')]">
    <header class="document-header">
      <div class="document-meta">
        <EpochBadge :epoch="document.epoch" />
        <h1 class="document-title">{{ document.title }}</h1>
        <p class="document-date">{{ formattedDate }}</p>
      </div>
      <div class="document-actions">
        <a href="#" class="action-link">BibTeX</a>
        <a href="#" class="action-link">Zitieren</a>
      </div>
    </header>

    <nav class="document-nav">
      <button class="nav-btn" disabled>&larr; Vorheriges</button>
      <button class="nav-btn" disabled>N&auml;chstes &rarr;</button>
    </nav>

    <div class="dual-container">
      <div class="dual-tabs" role="tablist">
        <button
          role="tab"
          id="tab-scan"
          :aria-selected="activeTab === 'scan'"
          :aria-controls="activeTab === 'scan' ? 'panel-scan' : undefined"
          class="tab-btn"
          :class="{ active: activeTab === 'scan' }"
          @click="activeTab = 'scan'"
        >
          Scan
        </button>
        <button
          role="tab"
          id="tab-transcription"
          :aria-selected="activeTab === 'transcription'"
          :aria-controls="activeTab === 'transcription' ? 'panel-transcription' : undefined"
          class="tab-btn"
          :class="{ active: activeTab === 'transcription' }"
          @click="activeTab = 'transcription'"
        >
          Transkription
        </button>
      </div>

      <div class="dual-panels">
        <div
          class="panel panel-scan"
          :class="{ hidden: activeTab !== 'scan' }"
          role="tabpanel"
          id="panel-scan"
          aria-labelledby="tab-scan"
        >
          <div class="scan-container">
            <img
              v-if="page.image_url"
              :src="page.image_url"
              :alt="'Scan Seite ' + (page.page_number || 1) + ' — ' + document.title"
              class="scan-image"
              :class="{ zoomed: imageZoomed }"
              @error="handleImageError"
              @click="toggleZoom"
            />
            <div class="scan-placeholder" style="display: none;">
              <div class="placeholder-inner">
                <span class="placeholder-icon">📄</span>
                <span class="placeholder-text">Scan nicht verf&uuml;gbar</span>
                <div class="placeholder-meta">
                  <p><strong>Titel:</strong> {{ document.title }}</p>
                  <p><strong>Datum:</strong> {{ formattedDate }}</p>
                  <p><strong>Typ:</strong> {{ document.type }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div
          class="panel panel-transcription"
          :class="{ hidden: activeTab !== 'transcription' }"
          role="tabpanel"
          id="panel-transcription"
          aria-labelledby="tab-transcription"
        >
          <div class="transcription-container">
            <p class="transcription-text">
              <template v-for="(segment, index) in transcriptionSegments" :key="index">
                <GapInline
                  v-if="segment.type === 'gap'"
                  :bbox-id="segment.bboxId"
                  :is-submitted="submittedBboxIds.includes(segment.bboxId)"
                  @gap-clicked="emit('gap-clicked', segment.bbox)"
                />
                <span v-else>{{ segment.content }}</span>
              </template>
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="dual-columns">
      <div class="column column-scan">
        <div class="scan-wrapper">
          <img
            v-if="page.image_url"
            :src="page.image_url"
            :alt="'Scan von ' + document.title"
            class="scan-image"
            :class="{ zoomed: imageZoomed }"
            @error="handleImageError"
            @click="toggleZoom"
          />
          <div class="scan-placeholder" style="display: none;">
            <div class="placeholder-inner">
              <span class="placeholder-icon">📄</span>
              <span class="placeholder-text">Scan nicht verf&uuml;gbar</span>
              <div class="placeholder-meta">
                <p><strong>Titel:</strong> {{ document.title }}</p>
                <p><strong>Datum:</strong> {{ formattedDate }}</p>
                <p><strong>Typ:</strong> {{ document.type }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="column column-transcription">
        <div class="transcription-wrapper">
          <p class="transcription-text">
            <template v-for="(segment, index) in transcriptionSegments" :key="index">
              <GapInline
                  v-if="segment.type === 'gap'"
                  :bbox-id="segment.bboxId"
                  :is-submitted="submittedBboxIds.includes(segment.bboxId)"
                  @gap-clicked="emit('gap-clicked', segment.bbox)"
                />
                <span v-else>{{ segment.content }}</span>
            </template>
          </p>
        </div>
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
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-m);
  gap: var(--space-l);
  flex-wrap: wrap;
}

.document-meta {
  flex: 1;
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
}

.document-actions {
  display: flex;
  gap: var(--space-m);
}

.action-link {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-epoch-primary);
  text-decoration: none;
  padding: var(--space-s) var(--space-m);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  transition: all var(--transition-fast);
}

.action-link:hover {
  background: var(--color-epoch-primary);
  color: var(--color-surface);
  border-color: var(--color-epoch-primary);
}

.document-nav {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-l);
  padding: var(--space-m) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.nav-btn {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-s);
}

.nav-btn:hover:not(:disabled) {
  color: var(--color-epoch-primary);
}

.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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
  transition: all var(--transition-fast);
}

.tab-btn:first-child {
  border-right: none;
  border-radius: 4px 0 0 4px;
}

.tab-btn:last-child {
  border-radius: 0 4px 4px 0;
}

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

.scan-wrapper {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E8E4DB;
  border-radius: 4px;
  overflow: hidden;
}

.scan-image {
  max-width: 100%;
  max-height: 600px;
  cursor: zoom-in;
  transition: transform var(--transition-fast);
  object-fit: contain;
}

.scan-image.zoomed {
  transform: scale(1.5);
  cursor: zoom-out;
}

.scan-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: var(--space-l);
}

.placeholder-inner {
  text-align: center;
  color: var(--color-text-secondary);
}

.placeholder-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: var(--space-m);
}

.placeholder-text {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  display: block;
  margin-bottom: var(--space-m);
}

.placeholder-meta {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  text-align: left;
  margin-top: var(--space-m);
  padding: var(--space-m);
  background: var(--color-surface);
  border-radius: 4px;
}

.placeholder-meta p {
  margin: var(--space-xs) 0;
}

.transcription-wrapper {
  min-height: 400px;
}

.transcription-text {
  font-family: var(--font-serif);
  font-size: 1rem;
  line-height: 1.75;
  color: var(--color-text-primary);
}

.panel {
  display: none;
}

.panel.hidden {
  display: none;
}

@media (max-width: 767px) {
  .dual-tabs {
    display: flex;
  }

  .dual-columns {
    display: none;
  }

  .panel {
    display: block;
  }

  .panel.hidden {
    display: none;
  }

  .panel-scan {
    background: var(--color-surface);
    border-radius: 8px;
    padding: var(--space-m);
  }

  .panel-transcription {
    background: var(--color-surface);
    border-radius: 8px;
    padding: var(--space-m);
  }

  .scan-container {
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #E8E4DB;
    border-radius: 4px;
  }

  .scan-container .scan-image {
    max-height: 400px;
  }

  .transcription-container {
    min-height: 200px;
  }
}
</style>
