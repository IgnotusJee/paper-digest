import client from './client';
import type { User } from '../types';

export const authApi = {
  login(username: string, password: string) {
    return client.post('/api/auth/login', { username, password });
  },
  logout() {
    return client.post('/api/auth/logout');
  },
  me() {
    return client.get<User>('/api/auth/me');
  },
};
