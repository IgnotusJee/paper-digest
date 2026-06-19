import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { User } from '@/types'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const initialized = ref(false)

  async function fetchUser() {
    try {
      const { data } = await authApi.getMe()
      user.value = data
    } catch {
      user.value = null
    } finally {
      initialized.value = true
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      await authApi.login(username, password)
      await fetchUser()
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    await authApi.logout()
    user.value = null
  }

  return { user, loading, initialized, fetchUser, login, logout }
})
