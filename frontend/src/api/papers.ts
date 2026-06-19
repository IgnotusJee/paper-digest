import client from './client';
import type { Paper } from '../types';

export interface ListPapersParams {
  page?: number;
  size?: number;
  sort?: 'created_at' | 'final_score' | 'keyword_score';
  order?: 'asc' | 'desc';
  bucket?: 'venue' | 'arxiv' | null;
}

export interface ListPapersResponse {
  items: Paper[];
  total: number;
  page: number;
  pages: number;
}

export const papersApi = {
  list(params: ListPapersParams) {
    return client.get<ListPapersResponse>('/api/papers', { params });
  },
  get(id: number) {
    return client.get<Paper>(`/api/papers/${id}`);
  },
  tag(id: number, tagType: 'interested' | 'not_interested' | 'read_later') {
    return client.post(`/api/papers/${id}/tag`, { tag_type: tagType });
  },
  removeTag(id: number) {
    return client.delete(`/api/papers/${id}/tag`);
  },
};
