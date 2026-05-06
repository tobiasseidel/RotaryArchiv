<script setup>
import { computed } from 'vue'
import EpochBadge from '@/components/EpochBadge.vue'

const props = defineProps({
  featured: {
    type: Object,
    required: true
  }
})

const formattedDate = computed(() => {
  const d = new Date(props.featured.date)
  return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' })
})

const epoch = computed(() => {
  return '30er'
})
</script>

<template>
  <div class="hero-block">
    <div class="hero-date-row">
      <span class="hero-date">{{ formattedDate }}</span>
      <EpochBadge :epoch="epoch" />
    </div>

    <blockquote class="hero-quote">
      &bdquo;{{ featured.quote_text }}&rdquo;
    </blockquote>

    <div class="hero-source">
      <RouterLink
        :to="'/dokument/' + featured.document_id"
        class="source-link"
      >
        {{ featured.quote_source }} &rarr;
      </RouterLink>
    </div>

    <div v-if="featured.person_slug" class="hero-person">
      <RouterLink
        :to="'/person/' + featured.person_slug"
        class="person-link"
      >
        Zur Person
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.hero-block {
  padding: var(--space-3xl) 0;
  max-width: 720px;
}

.hero-date-row {
  display: flex;
  align-items: center;
  gap: var(--space-m);
  margin-bottom: var(--space-l);
}

.hero-date {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.hero-quote {
  font-family: var(--font-serif);
  font-size: 2rem;
  font-style: italic;
  line-height: 1.4;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-l) 0;
  max-width: 720px;
}

.hero-source {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.source-link {
  color: var(--color-epoch-primary);
  text-decoration: none;
  font-weight: 500;
}

.source-link:hover {
  text-decoration: underline;
  color: var(--color-epoch-accent);
}

.hero-person {
  margin-top: var(--space-m);
}

.person-link {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-epoch-primary);
  text-decoration: none;
}

.person-link:hover {
  text-decoration: underline;
}
</style>
