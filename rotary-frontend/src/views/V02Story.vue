<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { useApi } from '@/composables/useApi'
import EpochBadge from '@/components/EpochBadge.vue'

const route = useRoute()
const { getStory } = useApi()

const story = ref(null)
const loading = ref(true)
const error = ref(null)

const renderedBody = computed(() => {
  if (!story.value?.body) return ''
  let html = marked(story.value.body, { breaks: true })
  if (story.value.sources?.length) {
    html = html.replace(/\[#(\d+)\]/g, (match, id) => {
      const sid = parseInt(id)
      const found = story.value.sources.some(s => s.id === sid)
      if (found) {
        return `<sup><a href="#source-${sid}" class="citation-link">[${id}]</a></sup>`
      }
      return match
    })
  }
  return html
})

const formattedDate = computed(() => {
  if (!story.value?.created_at) return ''
  return new Date(story.value.created_at).toLocaleDateString('de-DE', {
    day: 'numeric', month: 'long', year: 'numeric'
  })
})

onMounted(async () => {
  try {
    story.value = await getStory(route.params.slug)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="view-story">
    <div class="view-story-inner">
      <div v-if="loading" class="skeleton-story"></div>

      <div v-else-if="error" class="story-error">
        <h1>Story nicht gefunden</h1>
        <p>{{ error }}</p>
        <RouterLink to="/" class="back-link">Zur Startseite</RouterLink>
      </div>

      <article v-else-if="story" class="story-article">
        <header class="story-header">
          <div class="story-meta">
            <span class="story-date">{{ formattedDate }}</span>
            <EpochBadge v-if="story.epoch" :epoch="story.epoch" />
          </div>
          <h1 class="story-title">{{ story.title }}</h1>
          <p v-if="story.teaser" class="story-teaser">{{ story.teaser }}</p>
        </header>

        <div v-if="story.image_url" class="story-image">
          <img :src="story.image_url" :alt="story.title" />
        </div>

        <div class="story-body" v-html="renderedBody"></div>

        <footer v-if="story.sources?.length" class="story-sources">
          <h2 class="sources-title">Quellen</h2>
          <ol class="sources-list">
            <li v-for="(source, idx) in story.sources" :key="source.id" :id="'source-' + source.id" class="source-item">
              <span class="source-number">{{ idx + 1 }}.</span>
              <div class="source-content">
                <blockquote class="source-quote">
                  &bdquo;{{ source.note_text }}&rdquo;
                </blockquote>
                <div class="source-meta">
                  <span v-if="source.note_author" class="source-author">
                    &mdash; {{ source.note_author }}
                  </span>
                  <a v-if="source.document_unit_id"
                    :href="'/dokument/' + source.document_unit_id + (source.page_number ? '?page=' + source.page_number : '')"
                    class="source-doc-link" target="_blank">
                    &#128279; Zum Dokument
                  </a>
                </div>
              </div>
            </li>
          </ol>
        </footer>
      </article>
    </div>
  </div>
</template>

<style scoped>
.view-story {
  min-height: 100vh;
}

.view-story-inner {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-l);
}

.skeleton-story {
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

.story-error {
  text-align: center;
  padding: var(--space-3xl) 0;
}

.story-error h1 {
  font-family: var(--font-serif);
  font-size: 2rem;
  margin-bottom: var(--space-m);
}

.back-link {
  display: inline-block;
  margin-top: var(--space-l);
  color: var(--color-epoch-primary);
  text-decoration: none;
  font-weight: 500;
}

.back-link:hover {
  text-decoration: underline;
}

.story-header {
  margin-bottom: var(--space-2xl);
  padding-bottom: var(--space-xl);
  border-bottom: 1px solid var(--color-border);
}

.story-meta {
  display: flex;
  align-items: center;
  gap: var(--space-m);
  margin-bottom: var(--space-m);
}

.story-date {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.story-title {
  font-family: var(--font-serif);
  font-size: 2.5rem;
  line-height: 1.2;
  margin: 0 0 var(--space-m) 0;
  color: var(--color-text-primary);
}

.story-teaser {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin: 0;
}

.story-image {
  margin-bottom: var(--space-2xl);
}

.story-image img {
  width: 100%;
  height: auto;
  border-radius: 8px;
}

.story-body {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  line-height: 1.8;
  color: var(--color-text-primary);
}

.story-body :deep(h2) {
  font-size: 1.75rem;
  margin-top: var(--space-2xl);
  margin-bottom: var(--space-m);
  font-family: var(--font-serif);
}

.story-body :deep(h3) {
  font-size: 1.375rem;
  margin-top: var(--space-xl);
  margin-bottom: var(--space-m);
  font-family: var(--font-serif);
}

.story-body :deep(p) {
  margin-bottom: var(--space-m);
}

.story-body :deep(blockquote) {
  margin: var(--space-l) 0;
  padding: var(--space-m) var(--space-l);
  border-left: 4px solid var(--color-epoch-primary);
  background: var(--color-surface);
  font-style: italic;
  border-radius: 0 4px 4px 0;
}

.story-body :deep(ul) {
  margin-bottom: var(--space-m);
  padding-left: var(--space-l);
}

.story-body :deep(li) {
  margin-bottom: var(--space-xs);
}

.story-body :deep(strong) {
  font-weight: 700;
}

.story-body :deep(.citation-link) {
  color: var(--color-epoch-primary);
  text-decoration: none;
  font-weight: 700;
  font-size: 0.75rem;
}

.story-body :deep(.citation-link:hover) {
  text-decoration: underline;
}

.story-sources {
  margin-top: var(--space-3xl);
  padding-top: var(--space-xl);
  border-top: 2px solid var(--color-border);
}

.sources-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  margin-bottom: var(--space-l);
  color: var(--color-text-primary);
}

.sources-list {
  list-style: none;
  padding: 0;
  counter-reset: source-counter;
}

.source-item {
  margin-bottom: var(--space-l);
  padding: var(--space-m);
  background: var(--color-surface);
  border-radius: 4px;
  border-left: 3px solid var(--color-epoch-primary);
  display: flex;
  gap: var(--space-s);
}

.source-number {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-epoch-primary);
  min-width: 1.5em;
  line-height: 1.6;
}

.source-content {
  flex: 1;
  min-width: 0;
}

.source-quote {
  font-family: var(--font-serif);
  font-size: 1rem;
  line-height: 1.6;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs) 0;
  font-style: italic;
}

.source-meta {
  display: flex;
  align-items: center;
  gap: var(--space-m);
  flex-wrap: wrap;
}

.source-author {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.source-doc-link {
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-epoch-primary);
  text-decoration: none;
  font-weight: 600;
  white-space: nowrap;
}

.source-doc-link:hover {
  text-decoration: underline;
}
</style>
