<script setup>
import { useRoute } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useEpochStore } from '@/stores/epoch'
import PersonProfile from '@/components/PersonProfile.vue'
import EpochBadge from '@/components/EpochBadge.vue'

const route = useRoute()
const { getPerson } = useApi()
const epochStore = useEpochStore()

const slug = computed(() => route.params.slug)
const person = ref(null)
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    loading.value = true
    const data = await getPerson(slug.value)
    person.value = data
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
  <div class="view-person">
    <div v-if="loading" class="loading-state">
      <div class="skeleton-block"></div>
      <div class="skeleton-block short"></div>
      <div class="skeleton-block"></div>
    </div>

    <div v-else-if="error" class="error-state">
      <h1>Person nicht gefunden</h1>
      <p>Die gesuchte Person existiert nicht im RotaryArchiv.</p>
      <RouterLink to="/" class="back-link">← Zurück zur Startseite</RouterLink>
    </div>

    <div v-else-if="person.stub" class="stub-state">
      <div class="stub-content">
        <EpochBadge :epoch="person.epoch || '90er'" />
        <h1 class="stub-name">
          {{ person.epoch === '30er' ? 'Mitglied der 30er' : 'Mitglied der 90er' }}
        </h1>
        <p class="stub-explanation">
          Dieser Eintrag ist noch nicht öffentlich einsehbar.
          Das RotaryArchiv befindet sich im Aufbau und sammelt Informationen über ehemalige Mitglieder.
        </p>
        <p class="stub-explanation">
          Um vollständigen Zugang zu erhalten, melden Sie sich als Mitglied an.
        </p>
        <a href="#" class="login-cta">Jetzt einloggen</a>
      </div>
    </div>

    <PersonProfile v-else :person="person" />
  </div>
</template>

<style scoped>
.view-person {
  min-height: 50vh;
}

.loading-state {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-l);
  display: flex;
  flex-direction: column;
  gap: var(--space-m);
}

.skeleton-block {
  height: 200px;
  background: linear-gradient(90deg, var(--color-bg) 25%, var(--color-surface) 50%, var(--color-bg) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
}

.skeleton-block.short {
  height: 60px;
  width: 60%;
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

.stub-name {
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
</style>
