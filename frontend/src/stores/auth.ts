import { defineStore } from 'pinia';
import { ref } from 'vue';
import { authApi } from '../api/auth';
import type { User } from '../types';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null);
  const loading = ref(false);
  const initialized = ref(false);

  async function fetchUser() {
    loading.value = true;
    try {
      const res = await authApi.me();
      user.value = res.data;
      return res.data;
    } catch (err) {
      user.value = null;
      throw err;
    } finally {
      loading.value = false;
      initialized.value = true;
    }
  }

  async function login(username: string, password: string) {
    loading.value = true;
    try {
      await authApi.login(username, password);
      // Fetch user profile after successful login
      return await fetchUser();
    } finally {
      loading.value = false;
    }
  }

  async function logout() {
    loading.value = true;
    try {
      await authApi.logout();
    } finally {
      user.value = null;
      loading.value = false;
    }
  }

  return {
    user,
    loading,
    initialized,
    fetchUser,
    login,
    logout,
  };
});
