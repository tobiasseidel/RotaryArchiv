<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const query = ref('')

function submit() {
  const q = query.value.trim()
  if (!q) return
  router.push({ name: 'search', query: { q } })
}
</script>

<template>
  <form class="search-bar" @submit.prevent="submit" role="search">
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.3-4.3"/>
    </svg>
    <input
      v-model="query"
      class="search-input"
      type="search"
      placeholder="Personen, Dokumente, Orte …"
      aria-label="Suche"
    />
    <button v-if="query" class="search-clear" type="button" aria-label="Suche leeren" @click="query = ''">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 6 6 18M6 6l12 12"/>
      </svg>
    </button>
  </form>
</template>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: var(--space-s);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-s) var(--space-m);
  transition: border-color var(--transition-fast);
}

.search-bar:focus-within {
  border-color: var(--color-epoch-primary);
}

.search-icon {
  flex-shrink: 0;
  color: var(--color-stub);
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--color-stub);
}

.search-clear {
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-stub);
  padding: 2px;
  display: flex;
}

.search-clear:hover {
  color: var(--color-text-secondary);
}
</style>
