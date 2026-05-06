<script setup>
import { ref, computed } from 'vue'

const imageFailed = ref(false)

function handleImageError() {
  imageFailed.value = true
}
import EpochBadge from './EpochBadge.vue'

const props = defineProps({
  slug: {
    type: String,
    required: true
  },
  displayName: {
    type: String,
    required: true
  },
  epoch: {
    type: String,
    required: true,
    validator: (value) => ['30er', '90er'].includes(value)
  },
  isPublic: {
    type: Boolean,
    default: true
  },
  type: {
    type: String,
    required: true,
    validator: (value) => ['person', 'document'].includes(value)
  },
  portraitUrl: {
    type: String,
    default: ''
  },
  snippet: {
    type: String,
    default: ''
  }
})

const routePath = computed(() => {
  return props.type === 'person'
    ? `/person/${props.slug}`
    : `/dokument/${props.slug}`
})

const initials = computed(() => {
  const names = props.displayName.split(' ')
  return names.map(n => n[0]).join('').substring(0, 2).toUpperCase()
})

const anonymizedName = computed(() => {
  return props.epoch === '30er' ? 'Mitglied der 30er' : 'Mitglied der 90er'
})
</script>

<template>
  <article class="entity-card" :class="[`epoch-${epoch}`, { 'is-stub': !isPublic }]">
    <div v-if="isPublic" class="card-image">
      <img v-if="portraitUrl && !imageFailed" :src="portraitUrl" :alt="displayName" class="portrait" @error="handleImageError" />
      <div v-else class="initials-placeholder">{{ initials }}</div>
    </div>
    <div v-else class="card-image stub-image">
      <div class="initials-placeholder">{{ initials }}</div>
    </div>

    <div class="card-content">
      <EpochBadge v-if="isPublic" :epoch="epoch" />

      <h3 v-if="isPublic" class="card-title">
        <RouterLink :to="routePath">{{ displayName }}</RouterLink>
      </h3>
      <h3 v-else class="card-title stub-title">{{ anonymizedName }}</h3>

      <p v-if="isPublic && snippet" class="card-snippet">{{ snippet }}</p>
      <p v-if="!isPublic" class="card-stub-text">Dieser Inhalt ist nur für eingeloggte Mitglieder sichtbar.</p>
    </div>
  </article>
</template>

<style scoped>
.entity-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color var(--transition-fast);
}

.entity-card:hover:not(.is-stub) {
  border-color: var(--color-epoch-primary);
}

.is-stub {
  opacity: 0.6;
}

.card-image {
  aspect-ratio: 3 / 4;
  overflow: hidden;
  background: var(--color-bg);
}

.stub-image {
  opacity: 0.5;
}

.portrait {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.initials-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-epoch-badge);
  color: var(--color-epoch-primary);
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
}

.card-content {
  padding: var(--space-m);
  display: flex;
  flex-direction: column;
  gap: var(--space-s);
}

.card-title {
  font-family: var(--font-serif);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.3;
}

.card-title a {
  color: var(--color-text-primary);
  text-decoration: none;
}

.card-title a:hover {
  color: var(--color-epoch-primary);
}

.stub-title {
  color: var(--color-text-secondary);
  font-style: italic;
}

.card-snippet {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-stub-text {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-stub);
  font-style: italic;
}
</style>
