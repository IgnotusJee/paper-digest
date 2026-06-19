<template>
  <div class="login-wrapper">
    <n-card class="login-card" size="large">
      <div class="header">
        <span class="logo">📚</span>
        <h2>AI 论文日报系统</h2>
        <p>输入凭证以管理您的订阅与配额</p>
      </div>

      <n-form ref="formRef" :model="formValue" :rules="rules" @submit.prevent="handleLogin">
        <n-form-item label="用户名" path="username">
          <n-input
            v-model:value="formValue.username"
            placeholder="请输入用户名"
            clearable
            @keyup.enter="handleLogin"
          />
        </n-form-item>
        
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="formValue.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
            clearable
            @keyup.enter="handleLogin"
          />
        </n-form-item>

        <div v-if="errorMessage" class="error-alert">
          <n-alert title="登录失败" type="error">
            {{ errorMessage }}
          </n-alert>
        </div>

        <n-button
          type="primary"
          block
          attr-type="submit"
          :loading="loading"
          style="margin-top: 16px;"
        >
          登 录
        </n-button>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useMessage } from 'naive-ui';
import type { FormInst } from 'naive-ui';

const formRef = ref<FormInst | null>(null);
const formValue = ref({
  username: '',
  password: ''
});
const loading = ref(false);
const errorMessage = ref('');

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const message = useMessage();

const rules = {
  username: {
    required: true,
    message: '请输入用户名',
    trigger: 'blur'
  },
  password: {
    required: true,
    message: '请输入密码',
    trigger: 'blur'
  }
};

async function handleLogin() {
  formRef.value?.validate(async (errors) => {
    if (errors) return;

    loading.value = true;
    errorMessage.value = '';
    
    try {
      await authStore.login(formValue.value.username, formValue.value.password);
      message.success('登录成功');
      
      // Redirect to the URL they were trying to visit, or fallback to /
      const redirectPath = route.query.redirect as string;
      router.push(redirectPath || '/');
    } catch (err: any) {
      if (err.response) {
        if (err.response.status === 429) {
          errorMessage.value = '登录尝试次数过多，请在 5 分钟后再试';
        } else {
          errorMessage.value = err.response.data?.detail || '用户名或密码错误';
        }
      } else {
        errorMessage.value = '无法连接到后端服务器，请检查网络连接';
      }
    } finally {
      loading.value = false;
    }
  });
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f1f5f9;
}
.login-card {
  max-width: 400px;
  width: 90%;
  border-radius: 16px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
}
.header {
  text-align: center;
  margin-bottom: 24px;
}
.logo {
  font-size: 48px;
  display: block;
  margin-bottom: 8px;
}
.header h2 {
  font-size: 24px;
  margin: 0;
  color: #0f172a;
}
.header p {
  color: #64748b;
  margin: 8px 0 0;
  font-size: 14px;
}
.error-alert {
  margin-top: 12px;
}
</style>
