<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useEpochStore } from '@/stores/epoch'
import HeroBlock from '@/components/HeroBlock.vue'
import EntityCard from '@/components/EntityCard.vue'

const { getFeatured, getPersons } = useApi()
const epochStore = useEpochStore()

const featured = ref(null)
const persons = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [featuredData, personsData] = await Promise.all([
      getFeatured(),
      getPersons({ epoch: '30er' })
    ])
    featured.value = featuredData
    persons.value = personsData
  } catch (e) {
    console.error('Error loading home data:', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="view-home" :class="epochStore.epochClass">
    <div class="view-home-inner">
      <section class="hero-section">
        <HeroBlock v-if="featured" :featured="featured" />
        <div v-else-if="loading" class="skeleton-hero"></div>
      </section>

      <section class="persons-section">
        <h2 class="section-title">Erschlossene Personen</h2>
        <div class="persons-grid">
          <EntityCard
            v-for="person in persons"
            :key="person.id"
            :slug="person.slug"
            :display-name="person.display_name"
            :epoch="person.epoch"
            :is-public="person.is_public"
            type="person"
            :snippet="person.notes"
            :portrait-url="person.portrait_url"
            :born-year="person.born_year"
            :died-year="person.died_year"
          />
        </div>
      </section>

      <section class="epochs-section">
        <RouterLink to="/epochen" class="epoch-tile epoch-30er-tile">
          <span class="epoch-tile-label">Die 30er</span>
          <span class="epoch-tile-years">1927–1937</span>
          <span class="epoch-tile-desc">Die Gründungszeit</span>
        </RouterLink>

        <div class="epoch-tile epoch-90er-tile">
          <span class="epoch-tile-label">Die 90er</span>
          <span class="epoch-tile-years">1990–2008</span>
          <span class="epoch-tile-desc">Die Wiedergründung</span>
          <a href="#" class="epoch-tile-cta">Inhalte freischalten</a>
        </div>
      </section>

      <footer class="stats-footer">
        <p class="stats-line">
          {{ persons.length }} Personen erschlossen &middot;
          2 Dokumente &middot;
          0 Stories
        </p>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.view-home {
  min-height: 100vh;
}

.view-home-inner {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-l);
}

.hero-section {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-xl);
  margin-bottom: var(--space-xl);
}

.skeleton-hero {
  height: 200px;
  background: linear-gradient(90deg, var(--color-bg) 25%, var(--color-surface) 50%, var(--color-bg) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.persons-section {
  margin-bottom: var(--space-xl);
}

.section-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: var(--space-l);
  color: var(--color-text-primary);
}

.persons-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-l);
}

.epochs-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-l);
  margin-bottom: var(--space-xl);
}

.epoch-tile {
  display: flex;
  flex-direction: column;
  padding: var(--space-l);
  border-radius: 8px;
  text-decoration: none;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.epoch-tile:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(28, 25, 23, 0.12);
}

.epoch-30er-tile {
  background: var(--color-epoch-badge);
  border: 1px solid var(--color-border);
}

.epoch-90er-tile {
  background: var(--color-epoch-badge);
  border: 1px solid var(--color-border);
}

.epoch-tile-label {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-epoch-primary);
  margin-bottom: var(--space-xs);
}

.epoch-tile-years {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.epoch-tile-desc {
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  color: var(--color-text-primary);
}

.epoch-tile-cta {
  margin-top: auto;
  padding-top: var(--space-m);
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-epoch-primary);
  text-decoration: none;
}

.epoch-tile-cta:hover {
  text-decoration: underline;
}

.stats-footer {
  text-align: center;
  padding: var(--space-l) 0;
  border-top: 1px solid var(--color-border);
}

.stats-line {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

@media (max-width: 767px) {
  .persons-grid {
    grid-template-columns: 1fr;
  }

  .epochs-section {
    grid-template-columns: 1fr;
  }
}
</style>
