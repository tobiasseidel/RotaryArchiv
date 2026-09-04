<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

const navGroups = [
  {
    label: 'Dokumente',
    items: [
      { name: 'upload', label: 'Upload', icon: '↑' },
      { name: 'queue', label: 'Queue', icon: '◉' },
    ]
  },
  {
    label: 'Seiten',
    items: [
      { name: 'review', label: 'Review', icon: '✓' },
      { name: 'quality', label: 'Qualität', icon: '◆' },
    ]
  },
  {
    label: 'Erschließung',
    items: [
      { name: 'units', label: 'Units', icon: '□' },
      { name: 'persons', label: 'Personen', icon: '○' },
      { name: 'bboxes', label: 'BBoxen', icon: '▭' },
      { name: 'map', label: 'Karte', icon: '◈' },
      { name: 'events', label: 'Events', icon: '◎' },
      { name: 'notes', label: 'Notizen', icon: '»' },
    ]
  },
  {
    label: 'OCR & Analyse',
    items: [
      { name: 'ocr-settings', label: 'OCR-Sichtung', icon: '⚙' },
      { name: 'analysis', label: 'Analyse', icon: '◇' },
    ]
  },
  {
    label: 'Stories',
    items: [
      { name: 'stories', label: 'Stories', icon: '❦' },
    ]
  }
]
</script>

<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <RouterLink to="/" class="logo">RotaryArchiv</RouterLink>
        <span class="admin-badge">Admin</span>
      </div>

      <nav class="sidebar-nav">
        <div v-for="group in navGroups" :key="group.label" class="nav-group">
          <div class="nav-group-label">{{ group.label }}</div>
          <RouterLink
            v-for="item in group.items"
            :key="item.name"
            :to="{ name: item.name }"
            class="nav-item"
            :class="{ active: route.name === item.name }"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info">
          <span class="user-name">{{ authStore.user?.display_name }}</span>
          <span class="user-role">{{ authStore.user?.role }}</span>
        </div>
        <button @click="handleLogout" class="logout-btn">Abmelden</button>
      </div>
    </aside>

    <main class="admin-main">
      <slot></slot>
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 50;
}

.sidebar-header {
  padding: var(--space-m) var(--space-l);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  gap: var(--space-s);
}

.logo {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  text-decoration: none;
}

.admin-badge {
  font-family: var(--font-sans);
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--color-epoch-primary);
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-m) 0;
}

.nav-group {
  margin-bottom: var(--space-m);
}

.nav-group-label {
  font-family: var(--font-sans);
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-stub);
  padding: var(--space-xs) var(--space-l);
  margin-bottom: var(--space-xs);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-s);
  padding: var(--space-s) var(--space-l);
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: var(--color-bg);
  color: var(--color-text-primary);
  text-decoration: none;
}

.nav-item.active {
  background: var(--color-bg);
  color: var(--color-epoch-primary);
  border-left-color: var(--color-epoch-primary);
  font-weight: 600;
}

.nav-icon {
  font-size: 1rem;
  width: 20px;
  text-align: center;
}

.sidebar-footer {
  padding: var(--space-m) var(--space-l);
  border-top: 1px solid var(--color-border);
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: var(--space-s);
}

.user-name {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.user-role {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-stub);
}

.logout-btn {
  width: 100%;
  padding: var(--space-s) var(--space-m);
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  background: var(--color-bg);
  color: var(--color-text-primary);
  border-color: var(--color-text-secondary);
}

.admin-main {
  flex: 1;
  margin-left: 240px;
  padding: var(--space-xl);
  max-width: calc(100% - 240px);
}

@media (max-width: 768px) {
  .sidebar {
    width: 100%;
    position: relative;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }

  .admin-main {
    margin-left: 0;
    max-width: 100%;
    padding: var(--space-l);
  }
}
</style>
