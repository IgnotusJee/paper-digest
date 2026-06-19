import client from './client';
import type { Keyword } from '../types';

export interface ListKeywordsResponse {
  items: Keyword[];
  total: number;
}

export const keywordsApi = {
  list(category?: string) {
    return client.get<ListKeywordsResponse>('/api/keywords', { params: { category } });
  },
  create(keyword: string, weight: number, category: string, aliases: string[] | null) {
    return client.post<Keyword>('/api/keywords', { keyword, weight, category, aliases });
  },
  update(id: number, data: Partial<Omit<Keyword, 'id'>>) {
    return client.put<Keyword>(`/api/keywords/${id}`, data);
  },
  delete(id: number) {
    return client.delete(`/api/keywords/${id}`);
  },
  loadPreset(name: string) {
    return client.post('/api/keywords/preset', { name });
  },
};
