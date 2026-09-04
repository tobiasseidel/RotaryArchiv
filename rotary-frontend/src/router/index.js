import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/V01Home.vue')
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/V00Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/V11Upload.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/upload',
    name: 'upload',
    component: () => import('@/views/V11Upload.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/queue',
    name: 'queue',
    component: () => import('@/views/V12Queue.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/person/:slug',
    name: 'person',
    component: () => import('@/views/V03Person.vue')
  },
  {
    path: '/dokument/:id',
    name: 'document',
    component: () => import('@/views/V04Document.vue')
  },
  { path: '/suche', name: 'search', component: () => import('@/views/V05Search.vue') },
  { path: '/geschichte/:slug', name: 'story', component: () => import('@/views/V02Story.vue') },
  // Phase 2 (auskommentierte Platzhalter)
  // { path: '/epochen', name: 'epochs', component: () => import('@/views/V02Epochs.vue') },
  // { path: '/karte', name: 'map', component: () => import('@/views/V06Map.vue') },
  // { path: '/netzwerk', name: 'network', component: () => import('@/views/V07Network.vue') },
  // { path: '/geschichte-einreichen', name: 'story-submit', component: () => import('@/views/V09StorySubmit.vue') },
  // { path: '/korrektur-einreichen', name: 'correction-submit', component: () => import('@/views/V10CorrectionSubmit.vue') },
  // { path: '/profil', name: 'profile', component: () => import('@/views/V11Profile.vue') },
  // { path: '/ueber', name: 'about', component: () => import('@/views/V12About.vue') }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

// Route Guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Beim ersten Laden: User-Daten laden wenn Token vorhanden
  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
  }

  // Geschützte Routes
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  // Gast-Routes (z.B. Login) - wenn bereits angemeldet, weiterleiten
  if (to.meta.guest && authStore.isAuthenticated) {
    return next({ name: 'admin' })
  }

  next()
})
