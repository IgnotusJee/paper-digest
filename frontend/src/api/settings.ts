import client from './client';
import type { SystemConfig } from '../types';

export const settingsApi = {
  get() {
    return client.get<SystemConfig>('/api/settings');
  },
  update(config: SystemConfig) {
    return client.put<SystemConfig>('/api/settings', config);
  },
};
