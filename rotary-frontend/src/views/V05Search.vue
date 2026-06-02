<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSearch } from '@/composables/useSearch'
import { useEpochStore } from '@/stores/epoch'
import SearchBar from '@/components/SearchBar.vue'
import EntityCard from '@/components/EntityCard.vue'

const route = useRoute()
const router = useRouter()
const { search, loading, error } = useSearch()
const epochStore = useEpochStore()

const query = ref('')
const results = ref([])
const hasSearched = ref(false)

async function doSearch() {
  const q = query.value.trim()
  if (!q) return
  hasSearched.value = true
  try {
    results.value = await search(q)
  } catch {
    results.value = []
  }
}

onMounted(() => {
  if (route.query.q) {
    query.value = route.query.q
    doSearch()
  }
})

watch(() => route.query.q, (q) => {
  if (q) {
    query.value = q
    doSearch()
  } else {
    query.value = ''
    results.value = []
    hasSearched.value = false
  }
})

const persons = ref([])
const documents = ref([])

watch(results, (r) => {
  documents.value = r.filter(item => item.type === 'document')
  persons.value = r.filter(item => item.type === 'person')
}, { immediate: true })
</script>

<template>
  <div class="view-search" :class="epochStore.epochClass">
    <div class="view-search-inner">
      <div class="search-header">
        <h1 class="search-title">Suche</h1>
        <SearchBar />
      </div>

      <div v-if="loading" class="search-loading">
        <div class="skeleton-row" v-for="n in 3" :key="n"></div>
      </div>

      <div v-else-if="error" class="search-error">
        <p class="error-text">Fehler bei der Suche: {{ error }}</p>
      </div>

      <div v-else-if="hasSearched && persons.length === 0 && documents.length === 0" class="search-empty">
        <p class="empty-text">Keine Ergebnisse für <strong>&bdquo;{{ query }}&rdquo;</strong></p>
      </div>

      <div v-else-if="hasSearched" class="search-results">
        <section v-if="documents.length" class="result-section">
          <h2 class="section-title">Dokumente ({{ documents.length }})</h2>
          <div class="results-grid">
            <EntityCard
              v-for="doc in documents"
              :key="'d-' + doc.id"
              :slug="doc.slug"
              :display-name="doc.display_name"
              :epoch="doc.epoch || '30er'"
              :is-public="true"
              type="document"
              :snippet="doc.snippet"
            />
          </div>
        </section>

        <section v-if="persons.length" class="result-section">
          <h2 class="section-title">Personen ({{ persons.length }})</h2>
          <div class="results-grid">
            <EntityCard
              v-for="person in persons"
              :key="'p-' + person.id"
              :slug="person.slug"
              :display-name="person.display_name"
              :epoch="person.epoch || '30er'"
              :is-public="true"
              type="person"
              :snippet="person.snippet"
              :portrait-url="person.portrait_url"
            />
          </div>
        </section>
      </div>

      <div v-else class="search-idle">
        <p class="idle-text">Geben Sie einen Suchbegriff ein, um Personen und Dokumente im RotaryArchiv zu durchsuchen.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-search {
  min-height: 50vh;
}

.view-search-inner {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-xl) var(--space-l);
}

.search-header {
  margin-bottom: var(--space-xl);
}

.search-title {
  font-family: var(--font-serif);
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: var(--space-l);
  color: var(--color-text-primary);
}

.skeleton-row {
  height: 80px;
  background: linear-gradient(90deg, var(--color-bg) 25%, var(--color-surface) 50%, var(--color-bg) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
  margin-bottom: var(--space-m);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.search-error,
.search-empty,
.search-idle {
  text-align: center;
  padding: var(--space-2xl) 0;
}

.error-text {
  font-family: var(--font-sans);
  color: var(--color-error);
}

.empty-text,
.idle-text {
  font-family: var(--font-sans);
  font-size: 1rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.result-section {
  margin-bottom: var(--space-xl);
}

.section-title {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: var(--space-l);
  color: var(--color-text-primary);
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-l);
}

@media (max-width: 767px) {
  .results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
