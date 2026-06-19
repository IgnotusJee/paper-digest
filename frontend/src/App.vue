<script setup lang="ts">
import { NConfigProvider, NDialogProvider, NNotificationProvider, NMessageProvider, NLoadingBarProvider } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#6366f1',
    primaryColorHover: '#818cf8',
    primaryColorPressed: '#4f46e5',
    primaryColorSuppl: '#a5b4fc',
    infoColor: '#6366f1',
    successColor: '#10b981',
    warningColor: '#f59e0b',
    errorColor: '#ef4444',
    borderRadius: '10px',
    borderRadiusSmall: '8px',
    fontFamily: '"Inter", "Lato", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    fontSize: '14px',
    fontSizeMini: '11px',
    fontSizeTiny: '12px',
    fontSizeSmall: '13px',
    fontSizeMedium: '14px',
    fontSizeLarge: '15px',
    fontSizeHuge: '16px',
    lineHeight: '1.6',
    borderColor: '#e5e7eb',
    dividerColor: '#f3f4f6',
    hoverColor: '#f9fafb',
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
    borderRadius: '14px',
    borderColor: '#f0f0f0',
    color: '#ffffff',
    titleFontSizeMedium: '15px',
    titleFontWeight: '600',
    paddingMedium: '20px',
  },
  Button: {
    borderRadiusMedium: '10px',
    borderRadiusSmall: '8px',
    fontWeightStrong: '600',
    paddingMedium: '0 20px',
    heightMedium: '38px',
    heightSmall: '32px',
  },
  Input: {
    borderRadius: '10px',
    heightMedium: '40px',
    color: '#ffffff',
    colorFocus: '#ffffff',
    borderHover: '#6366f1',
    borderFocus: '#6366f1',
    boxShadowFocus: '0 0 0 3px rgba(99, 102, 241, 0.15)',
    caretColor: '#6366f1',
  },
  Tag: {
    borderRadius: '8px',
    fontWeight: '500',
  },
  Menu: {
    borderRadius: '8px',
    itemHeightMedium: '42px',
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

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
  font-family: 'Inter', 'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f8fafc;
  color: #1e293b;
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
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}

.n-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.n-button {
  font-weight: 500;
}

.n-tag {
  font-weight: 500;
}
</style>
