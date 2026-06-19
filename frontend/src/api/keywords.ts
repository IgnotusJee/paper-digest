import client from './client'
import type { Keyword } from '@/types'

export function listKeywords(category?: string) {
  return client.get<{ items: Keyword[]; total: number }>('/api/keywords', {
    params: category ? { category } : {},
  })
}

export function createKeyword(data: Partial<Keyword>) {
  return client.post('/api/keywords', data)
}

export function updateKeyword(id: number, data: Partial<Keyword>) {
  return client.put(`/api/keywords/${id}`, data)
}

export function deleteKeyword(id: number) {
  return client.delete(`/api/keywords/${id}`)
}

export function loadPreset(name: string) {
  return client.post('/api/keywords/preset', { name })
}
