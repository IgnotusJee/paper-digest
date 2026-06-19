<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NCard, NForm, NFormItem, NInput, NButton, NText, NIcon, useMessage } from 'naive-ui'
import { LogInOutline, DocumentTextOutline } from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const msg = useMessage()

const form = ref({ username: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    msg.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    const redirect = (route.query.redirect as string) || '/digest'
    router.push(redirect)
  } catch (err: any) {
    const status = err.response?.status
    if (status === 429) {
      msg.error('登录尝试过于频繁，请稍后再试')
    } else if (status === 401) {
      msg.error('用户名或密码错误')
    } else {
      msg.error('登录失败，请重试')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-shape bg-shape-1"></div>
      <div class="bg-shape bg-shape-2"></div>
      <div class="bg-shape bg-shape-3"></div>
    </div>

    <div class="login-container">
      <div class="login-brand">
        <div class="brand-icon">
          <NIcon :size="32" color="#fff"><DocumentTextOutline /></NIcon>
        </div>
        <h1 class="brand-title">Paper Digest</h1>
        <p class="brand-subtitle">AI 驱动的论文日报系统</p>
      </div>

      <NCard class="login-card">
        <div class="card-header">
          <h2 class="card-title">欢迎回来</h2>
          <p class="card-desc">登录以查看今日推荐</p>
        </div>

        <NForm @submit.prevent="handleLogin" size="large">
          <NFormItem label="用户名" :show-label="false">
            <NInput
              v-model:value="form.username"
              placeholder="用户名"
              @keyup.enter="handleLogin"
              :input-props="{ autocomplete: 'username' }"
            />
          </NFormItem>
          <NFormItem label="密码" :show-label="false">
            <NInput
              v-model:value="form.password"
              type="password"
              placeholder="密码"
              show-password-on="click"
              @keyup.enter="handleLogin"
              :input-props="{ autocomplete: 'current-password' }"
            />
          </NFormItem>
          <NButton
            type="primary"
            block
            :loading="loading"
            @click="handleLogin"
            class="login-btn"
          >
            <template #icon>
              <NIcon><LogInOutline /></NIcon>
            </template>
            登录
          </NButton>
        </NForm>
      </NCard>

      <p class="login-footer">
        <span class="footer-dot"></span>
        仅限授权设备访问
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}

.bg-shape-1 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%);
  top: -150px;
  right: -100px;
}

.bg-shape-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%);
  bottom: -100px;
  left: -100px;
}

.bg-shape-3 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #67e8f9 0%, #22d3ee 100%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.2;
}

.login-container {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 420px;
  padding: 20px;
}

.login-brand {
  text-align: center;
  margin-bottom: 36px;
}

.brand-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
}

.brand-title {
  font-size: 32px;
  font-weight: 800;
  color: #111827;
  margin: 0;
  letter-spacing: -0.5px;
}

.brand-subtitle {
  font-size: 15px;
  color: #6b7280;
  margin-top: 8px;
  font-weight: 400;
}

.login-card {
  width: 100%;
  border-radius: 20px !important;
  box-shadow: 0 4px 40px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.8) !important;
  backdrop-filter: blur(20px);
}

.card-header {
  text-align: center;
  margin-bottom: 28px;
}

.card-title {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.card-desc {
  font-size: 14px;
  color: #9ca3af;
  margin-top: 6px;
}

.login-btn {
  height: 46px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  border-radius: 12px !important;
  margin-top: 8px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3) !important;
  transition: all 0.2s ease;
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(99, 102, 241, 0.4) !important;
}

.login-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 28px;
  font-size: 13px;
  color: #9ca3af;
}

.footer-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}
</style>
