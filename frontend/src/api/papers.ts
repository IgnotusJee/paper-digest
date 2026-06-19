import client from './client'
import type { ListPapersResponse, Paper, TagType } from '@/types'

export interface ListPapersParams {
  page?: number
  size?: number
  sort?: string
  order?: string
  bucket?: string
}

export function listPapers(params: ListPapersParams = {}) {
  return client.get<ListPapersResponse>('/api/papers', { params })
}

export function getPaper(id: number) {
  return client.get<Paper>(`/api/papers/${id}`)
}

export function addTag(paperId: number, tagType: TagType) {
  return client.post(`/api/papers/${paperId}/tag`, { tag_type: tagType })
}

export function removeTag(paperId: number) {
  return client.delete(`/api/papers/${paperId}/tag`)
}
