import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/V01Home.vue')
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
  // Phase 2 (auskommentierte Platzhalter)
  // { path: '/epochen', name: 'epochs', component: () => import('@/views/V02Epochs.vue') },
  // { path: '/karte', name: 'map', component: () => import('@/views/V06Map.vue') },
  // { path: '/netzwerk', name: 'network', component: () => import('@/views/V07Network.vue') },
  // { path: '/geschichte/:slug', name: 'story', component: () => import('@/views/V08StoryDetail.vue') },
  // { path: '/geschichte-einreichen', name: 'story-submit', component: () => import('@/views/V09StorySubmit.vue') },
  // { path: '/korrektur-einreichen', name: 'correction-submit', component: () => import('@/views/V10CorrectionSubmit.vue') },
  // { path: '/profil', name: 'profile', component: () => import('@/views/V11Profile.vue') },
  // { path: '/ueber', name: 'about', component: () => import('@/views/V12About.vue') }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})
