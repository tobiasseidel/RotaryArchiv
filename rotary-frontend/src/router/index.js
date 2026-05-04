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
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})
