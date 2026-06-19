import client from './client'
import type { DigestHistory } from '@/types'

export function getTodayDigest() {
  return client.get<DigestHistory>('/api/digest')
}

export function getDigestByDate(dateStr: string) {
  return client.get<DigestHistory>(`/api/digest/${dateStr}`)
}
