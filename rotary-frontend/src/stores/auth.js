import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API_BASE = '/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('rotary_token') || null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEditor = computed(() => ['admin', 'editor'].includes(user.value?.role))

  async function login(username, password) {
    const res = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'same-origin'
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Anmeldung fehlgeschlagen')
    }

    const data = await res.json()
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('rotary_token', data.access_token)
  }

  async function logout() {
    await fetch(`${API_BASE}/logout`, {
      method: 'POST',
      credentials: 'same-origin'
    })
    token.value = null
    user.value = null
    localStorage.removeItem('rotary_token')
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const res = await fetch(`${API_BASE}/me`, {
        credentials: 'same-origin'
      })
      if (res.ok) {
        user.value = await res.json()
      } else {
        token.value = null
        user.value = null
        localStorage.removeItem('rotary_token')
      }
    } catch {
      token.value = null
      user.value = null
      localStorage.removeItem('rotary_token')
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    isAdmin,
    isEditor,
    login,
    logout,
    fetchMe
  }
})
