import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../components/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/digest',
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
      },
      {
        path: 'digest',
        name: 'Digest',
        component: () => import('../views/Digest.vue'),
      },
      {
        path: 'papers',
        name: 'Papers',
        component: () => import('../views/Papers.vue'),
      },
      {
        path: 'papers/:id',
        name: 'PaperDetail',
        component: () => import('../views/PaperDetail.vue'),
      },
      {
        path: 'keywords',
        name: 'Keywords',
        component: () => import('../views/Keywords.vue'),
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/Settings.vue'),
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  // Try to load current user once if not initialized
  if (!authStore.initialized) {
    try {
      await authStore.fetchUser();
    } catch (e) {
      // Ignore 401/other failures here, handled by meta checks below
    }
  }

  const isAuthenticated = !!authStore.user;

  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
  } else if (to.name === 'Login' && isAuthenticated) {
    next({ name: 'Digest' });
  } else {
    next();
  }
});

export default router;
