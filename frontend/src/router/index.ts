import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/components/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/digest' },
        { path: 'dashboard', name: 'dashboard', component: () => import('@/views/Dashboard.vue') },
        { path: 'digest', name: 'digest', component: () => import('@/views/Digest.vue') },
        { path: 'papers', name: 'papers', component: () => import('@/views/Papers.vue') },
        { path: 'papers/:id', name: 'paper-detail', component: () => import('@/views/PaperDetail.vue') },
        { path: 'keywords', name: 'keywords', component: () => import('@/views/Keywords.vue') },
        { path: 'settings', name: 'settings', component: () => import('@/views/Settings.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) {
    await auth.fetchUser()
  }
  if (to.meta.requiresAuth !== false && !auth.user) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && auth.user) {
    return '/digest'
  }
})

export default router
