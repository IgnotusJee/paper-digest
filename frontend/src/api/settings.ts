import client from './client'
import type { SystemConfig } from '@/types'

export function getSettings() {
  return client.get<SystemConfig>('/api/settings')
}

export function updateSettings(data: Partial<SystemConfig>) {
  return client.put<SystemConfig>('/api/settings', data)
}
