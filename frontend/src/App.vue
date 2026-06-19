<script setup lang="ts">
import { NConfigProvider, NDialogProvider, NNotificationProvider, NMessageProvider, NLoadingBarProvider } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#2563eb',
    primaryColorHover: '#1d4ed8',
    primaryColorPressed: '#1e40af',
    primaryColorSuppl: '#93c5fd',
    infoColor: '#2563eb',
    successColor: '#059669',
    warningColor: '#d97706',
    errorColor: '#dc2626',
    borderRadius: '12px',
    borderRadiusSmall: '10px',
    fontFamily: '"Lato", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    fontSize: '14px',
    fontSizeMini: '11px',
    fontSizeTiny: '12px',
    fontSizeSmall: '13px',
    fontSizeMedium: '14px',
    fontSizeLarge: '15px',
    fontSizeHuge: '16px',
    lineHeight: '1.6',
    borderColor: '#e2e8f0',
    dividerColor: '#e5e7eb',
    hoverColor: '#f8fafc',
    cardColor: '#ffffff',
    modalColor: '#ffffff',
    popoverColor: '#ffffff',
    tableColor: '#ffffff',
    inputColor: '#ffffff',
    actionColor: '#f9fafb',
    tagColor: '#f3f4f6',
    closeIconColor: '#9ca3af',
    closeIconColorHover: '#6b7280',
    placeholderColor: '#9ca3af',
    clearColor: '#9ca3af',
    clearColorHover: '#6b7280',
    clearColorPressed: '#4b5563',
  },
  Card: {
    borderRadius: '12px',
    borderColor: '#e2e8f0',
    color: '#ffffff',
    titleFontSizeMedium: '15px',
    titleFontWeight: '600',
    paddingMedium: '20px',
  },
  Button: {
    borderRadiusMedium: '10px',
    borderRadiusSmall: '10px',
    fontWeightStrong: '600',
    paddingMedium: '0 20px',
    heightMedium: '40px',
    heightSmall: '32px',
  },
  Input: {
    borderRadius: '10px',
    heightMedium: '42px',
    color: '#ffffff',
    colorFocus: '#ffffff',
    borderHover: '#2563eb',
    borderFocus: '#2563eb',
    boxShadowFocus: '0 0 0 3px rgba(37, 99, 235, 0.14)',
    caretColor: '#2563eb',
  },
  Tag: {
    borderRadius: '999px',
    fontWeight: '500',
  },
  Menu: {
    borderRadius: '10px',
    itemHeightMedium: '44px',
    itemIconSize: '20px',
  },
  DataTable: {
    borderRadius: '12px',
    thFontWeight: '600',
  },
  Message: {
    borderRadius: '10px',
  },
  Notification: {
    borderRadius: '12px',
  },
  Alert: {
    borderRadius: '12px',
  },
}
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NDialogProvider>
      <NNotificationProvider>
        <NMessageProvider>
          <NLoadingBarProvider>
            <RouterView />
          </NLoadingBarProvider>
        </NMessageProvider>
      </NNotificationProvider>
    </NDialogProvider>
  </NConfigProvider>
</template>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 14px;
  -webkit-text-size-adjust: 100%;
}

body {
  font-family: 'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.05), transparent 30%),
    linear-gradient(180deg, #f8fafc 0%, #f3f7fb 100%);
  color: #0f172a;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  line-height: 1.6;
}

a {
  color: inherit;
  text-decoration: none;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.n-card {
  transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}

.n-card:hover {
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.05);
}

.n-button {
  font-weight: 600;
}

.n-tag {
  font-weight: 500;
}
</style>
