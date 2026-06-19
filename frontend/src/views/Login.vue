<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NCard, NForm, NFormItem, NInput, NButton, NIcon, useMessage, NTag } from 'naive-ui'
import {
  LogInOutline,
  DocumentTextOutline,
  SparklesOutline,
  GitNetworkOutline,
  MailOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const msg = useMessage()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const productSignals = [
  { label: '每日精选', icon: SparklesOutline },
  { label: '论文解读', icon: DocumentTextOutline },
  { label: '关键词订阅', icon: GitNetworkOutline },
]

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
    <div class="login-container">
      <div class="login-brand-panel">
        <div class="brand-topline">
          <span class="status-dot"></span>
          AI research briefings
        </div>

        <div class="login-brand">
          <div class="brand-icon">
            <NIcon :size="28" color="#eff6ff"><DocumentTextOutline /></NIcon>
          </div>
          <h1 class="brand-title">Paper Digest</h1>
          <p class="brand-subtitle">为 AI researcher 提供每日论文阅读、筛选与推送。</p>
        </div>

        <div class="signal-row">
          <NTag v-for="signal in productSignals" :key="signal.label" round :bordered="false" class="signal-tag">
            <template #icon>
              <NIcon :component="signal.icon" />
            </template>
            {{ signal.label }}
          </NTag>
        </div>

        <div class="brand-metrics">
          <div class="metric-block">
            <span class="metric-value">Venue + arXiv</span>
            <span class="metric-label">双通道来源</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">中文摘要</span>
            <span class="metric-label">面向快速扫读</span>
          </div>
        </div>
      </div>

      <NCard class="login-card" :bordered="false">
        <div class="card-header">
          <div class="card-badge">
            <NIcon :size="14"><MailOutline /></NIcon>
            Secure access
          </div>
          <h2 class="card-title">登录研究面板</h2>
          <p class="card-desc">查看今日 digest、关键词追踪与论文库。</p>
        </div>

        <NForm @submit.prevent="handleLogin" size="large">
          <NFormItem label="用户名">
            <NInput
              v-model:value="form.username"
              placeholder="用户名"
              @keyup.enter="handleLogin"
              :input-props="{ autocomplete: 'username' }"
            />
          </NFormItem>
          <NFormItem label="密码">
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
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.login-container {
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(360px, 420px);
  gap: 28px;
  align-items: stretch;
}

.login-brand-panel {
  padding: 40px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 12px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(248, 250, 252, 0.92) 100%),
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 32%);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.06);
}

.brand-topline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #475569;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.9);
  border: 1px solid #e2e8f0;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #2563eb;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
}

.login-brand {
  margin-top: 28px;
  margin-bottom: 24px;
  max-width: 520px;
}

.brand-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: 0 16px 28px rgba(37, 99, 235, 0.22);
}

.brand-title {
  font-size: 42px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.03em;
  line-height: 1.05;
}

.brand-subtitle {
  font-size: 17px;
  color: #475569;
  margin-top: 14px;
  font-weight: 400;
  max-width: 28ch;
}

.signal-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.signal-tag {
  background: #eff6ff !important;
  color: #1d4ed8 !important;
}

.brand-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid #e2e8f0;
}

.metric-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.metric-label {
  font-size: 13px;
  color: #64748b;
}

.login-card {
  width: 100%;
  border-radius: 12px !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  background: rgba(255, 255, 255, 0.96) !important;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.08) !important;
  align-self: center;
}

.card-header {
  margin-bottom: 24px;
}

.card-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
  font-size: 12px;
  margin-bottom: 14px;
}

.card-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.card-desc {
  font-size: 14px;
  color: #64748b;
  margin-top: 8px;
}

.login-btn {
  height: 44px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  margin-top: 8px;
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
  border: none !important;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.2) !important;
  transition: all 0.2s ease;
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 28px rgba(37, 99, 235, 0.25) !important;
}

@media (max-width: 960px) {
  .login-container {
    grid-template-columns: 1fr;
  }

  .login-brand-panel {
    padding: 28px;
  }

  .brand-title {
    font-size: 34px;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 20px;
  }

  .brand-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
