import client from './client';
import type { DigestHistory } from '../types';

export const digestApi = {
  getToday() {
    return client.get<DigestHistory>('/api/digest');
  },
  getByDate(dateStr: string) {
    return client.get<DigestHistory>(`/api/digest/${dateStr}`);
  },
};
