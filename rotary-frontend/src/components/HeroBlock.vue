<script setup>
import { computed } from 'vue'
import EpochBadge from '@/components/EpochBadge.vue'

const props = defineProps({
  featured: {
    type: Object,
    required: true
  }
})

const isStory = computed(() => !!props.featured.slug && props.featured.slug.length > 0)

const displayDate = computed(() => {
  if (isStory.value) return formatDate(props.featured.created_at)
  return formatDate(props.featured.date)
})

const displayEpoch = computed(() => {
  if (isStory.value) return props.featured.epoch
  return '30er'
})

function formatDate(d) {
  if (!d) return ''
  const date = new Date(d)
  return date.toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' })
}
</script>

<template>
  <div class="hero-block">
    <div class="hero-date-row">
      <span class="hero-date">{{ displayDate }}</span>
      <EpochBadge :epoch="displayEpoch" />
    </div>

    <template v-if="isStory">
      <h2 class="hero-title">
        <RouterLink :to="'/geschichte/' + featured.slug" class="hero-title-link">
          {{ featured.title }}
        </RouterLink>
      </h2>
      <p class="hero-teaser">{{ featured.teaser }}</p>
      <div class="hero-source">
        <RouterLink :to="'/geschichte/' + featured.slug" class="source-link">
          Weiterlesen &rarr;
        </RouterLink>
      </div>
    </template>

    <template v-else>
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
    </template>
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

.hero-title {
  font-family: var(--font-serif);
  font-size: 2.5rem;
  line-height: 1.2;
  margin: 0 0 var(--space-m) 0;
  max-width: 720px;
}

.hero-title-link {
  color: var(--color-text-primary);
  text-decoration: none;
}

.hero-title-link:hover {
  color: var(--color-epoch-primary);
}

.hero-teaser {
  font-family: var(--font-serif);
  font-size: 1.2rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-l) 0;
  max-width: 720px;
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
