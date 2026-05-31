<script setup>
import { ref, computed } from 'vue'

const imageFailed = ref(false)

function handleImageError() {
  imageFailed.value = true
}
import EpochBadge from './EpochBadge.vue'
import DocumentLinkPanel from './DocumentLinkPanel.vue'
import EntityCard from './EntityCard.vue'

const props = defineProps({
  person: {
    type: Object,
    required: true
  }
})

const lifespan = computed(() => {
  const born = props.person.born_year || 'unbekannt'
  const died = props.person.died_year ? `– ${props.person.died_year}` : ''
  return `${born} ${died}`.trim()
})

const initials = computed(() => {
  const names = props.person.display_name.split(' ')
  return names.map(n => n[0]).join('').substring(0, 2).toUpperCase()
})

const membershipStatus = computed(() => {
  if (!props.person.membership) return null
  if (!props.person.membership.left) {
    return 'Mitgliedschaft bis Auflösung des Clubs 1937'
  }
  return null
})
</script>

<template>
  <div class="person-profile" :class="`epoch-${person.epoch}`">
    <section class="portrait-block">
      <div class="portrait-wrapper">
        <img
          v-if="person.portrait_url && !imageFailed"
          :src="person.portrait_url"
          :alt="person.display_name"
          class="portrait-img"
          @error="handleImageError"
        />
        <div v-else class="portrait-placeholder">
          <span class="initials">{{ initials }}</span>
        </div>
      </div>

      <div class="person-info">
        <h1 class="person-name">{{ person.display_name }}</h1>
        <p class="person-lifespan">{{ lifespan }}</p>
        <EpochBadge :epoch="person.epoch" />
        <p v-if="person.notes" class="person-notes">{{ person.notes }}</p>
      </div>
    </section>

    <section v-if="person.membership" class="membership-block">
      <h2 class="section-title">Mitgliedschaft</h2>

      <div v-if="person.membership.joined_quote" class="membership-entry">
        <blockquote class="membership-quote">
          {{ person.membership.joined_quote }}
        </blockquote>
        <p class="membership-date">{{ person.membership.joined }}</p>
        <DocumentLinkPanel
          v-if="person.membership.joined_document_id"
          :document-id="person.membership.joined_document_id"
          label="Aufnahme-Protokoll"
        />
      </div>

      <div v-if="person.membership.left_quote" class="membership-entry">
        <blockquote class="membership-quote">
          {{ person.membership.left_quote }}
        </blockquote>
        <p class="membership-date">{{ person.membership.left }}</p>
        <DocumentLinkPanel
          v-if="person.membership.left_document_id"
          :document-id="person.membership.left_document_id"
          label="Austritts-Protokoll"
        />
      </div>

      <p v-if="membershipStatus" class="membership-status">
        {{ membershipStatus }}
      </p>

      <p v-if="person.membership.role" class="membership-role">
        Rolle: {{ person.membership.role }}
      </p>
    </section>

    <section v-if="person.attendance" class="attendance-block">
      <h2 class="section-title">Teilnahme</h2>
      <div class="attendance-bar-wrapper">
        <div
          class="attendance-bar"
          :style="{ width: `${(person.attendance.present / person.attendance.total) * 100}%` }"
        ></div>
      </div>
      <p class="attendance-label">
        {{ person.attendance.present }} von {{ person.attendance.total }} Sitzungen anwesend ({{ person.attendance.period }})
      </p>
    </section>

    <section class="timeline-block">
      <h2 class="section-title">Zeitstrahl</h2>
      <div v-if="person.timeline && person.timeline.length > 0" class="timeline-list">
        <div
          v-for="(item, index) in person.timeline"
          :key="index"
          class="timeline-item"
        >
          <span class="timeline-date">{{ item.date }}</span>
          <p class="timeline-snippet">{{ item.snippet }}</p>
          <DocumentLinkPanel
            v-if="item.document_id"
            :document-id="item.document_id"
            label="Dokument"
          />
        </div>
      </div>
      <p v-else class="timeline-empty">Zeitstrahl wird noch erschlossen.</p>
    </section>

    <section v-if="person.network && person.network.nodes && person.network.nodes.length > 0" class="network-block">
      <h2 class="section-title">Netzwerk</h2>
      <div class="network-nodes">
        <EntityCard
          v-for="node in person.network.nodes"
          :key="node.slug"
          :slug="node.slug"
          :display-name="node.display_name"
          :epoch="node.epoch || person.epoch"
          :is-public="true"
          type="person"
          :snippet="node.notes"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.person-profile {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-l);
}

.section-title {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: var(--space-m);
  color: var(--color-text-primary);
}

.portrait-block {
  display: flex;
  gap: var(--space-l);
  margin-bottom: var(--space-xl);
}

.portrait-wrapper {
  flex-shrink: 0;
  width: 200px;
}

.portrait-img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 8px;
}

.portrait-placeholder {
  width: 100%;
  aspect-ratio: 3 / 4;
  background: var(--color-epoch-badge);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.initials {
  font-family: var(--font-serif);
  font-size: 3rem;
  font-weight: 700;
  color: var(--color-epoch-primary);
}

.person-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-s);
}

.person-name {
  font-family: var(--font-serif);
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--color-text-primary);
  margin: 0;
}

.person-lifespan {
  font-family: var(--font-sans);
  font-size: 1rem;
  color: var(--color-text-secondary);
}

.person-notes {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-top: var(--space-s);
}

.membership-block,
.attendance-block,
.timeline-block,
.network-block {
  margin-bottom: var(--space-xl);
}

.membership-entry {
  margin-bottom: var(--space-m);
}

.membership-quote {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: 1rem;
  color: var(--color-text-primary);
  border-left: none;
  padding: 0;
  margin: 0 0 var(--space-xs) 0;
}

.membership-date {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.membership-status {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  font-style: italic;
  margin-top: var(--space-s);
}

.membership-role {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-primary);
  margin-top: var(--space-s);
}

.attendance-bar-wrapper {
  background: var(--color-bg);
  border-radius: 4px;
  height: 8px;
  overflow: hidden;
  margin-bottom: var(--space-s);
}

.attendance-bar {
  height: 100%;
  background: var(--color-epoch-primary);
  border-radius: 4px;
  transition: width var(--transition-page);
}

.attendance-label {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-m);
}

.timeline-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.timeline-date {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.timeline-snippet {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: 1rem;
  color: var(--color-text-primary);
  margin: 0;
}

.timeline-empty {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  font-style: italic;
}

.network-nodes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-m);
}

@media (max-width: 768px) {
  .portrait-block {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .portrait-wrapper {
    width: 160px;
  }
}
</style>
