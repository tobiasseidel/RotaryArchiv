<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="admin-page">
    <div class="admin-header">
      <h1>Admin-Bereich</h1>
      <div class="admin-user">
        <span>{{ authStore.user?.display_name }}</span>
        <span class="admin-role">{{ authStore.user?.role }}</span>
        <button @click="handleLogout" class="logout-button">Abmelden</button>
      </div>
    </div>

    <div class="admin-content">
      <p>Willkommen im Admin-Bereich.</p>
      <p>Hier werden in Phase B die Admin-Funktionen implementiert.</p>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.admin-header h1 {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  color: var(--color-text-primary);
  margin: 0;
}

.admin-user {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-sans);
  font-size: 0.875rem;
}

.admin-role {
  background: var(--color-epoch-primary);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
}

.logout-button {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.logout-button:hover {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.admin-content {
  font-family: var(--font-sans);
  color: var(--color-text-secondary);
}
</style>
