<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true

  try {
    await authStore.login(username.value, password.value)
    router.push('/admin')
  } catch (e) {
    error.value = e.message || 'Anmeldung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>RotaryArchiv</h1>
        <p>Anmeldung</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">Benutzername</label>
          <input
            id="username"
            v-model="username"
            type="text"
            required
            autocomplete="username"
            placeholder="Benutzername eingeben"
          />
        </div>

        <div class="form-group">
          <label for="password">Passwort</label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            autocomplete="current-password"
            placeholder="Passwort eingeben"
          />
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <button type="submit" :disabled="loading" class="login-button">
          <span v-if="loading">Anmelden...</span>
          <span v-else>Anmelden</span>
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}

.login-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 40px;
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  color: var(--color-text-primary);
  margin: 0 0 8px 0;
}

.login-header p {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

.form-group input {
  font-family: var(--font-sans);
  font-size: 1rem;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-epoch-primary);
}

.error-message {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: #dc2626;
  padding: 12px;
  background: #fef2f2;
  border-radius: 6px;
}

.login-button {
  font-family: var(--font-sans);
  font-size: 1rem;
  font-weight: 500;
  padding: 12px;
  background: var(--color-epoch-primary);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.login-button:hover:not(:disabled) {
  background: var(--color-epoch-primary-dark);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
