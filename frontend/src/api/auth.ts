import client from './client'

export function login(username: string, password: string) {
  return client.post('/api/auth/login', { username, password })
}

export function logout() {
  return client.post('/api/auth/logout')
}

export function getMe() {
  return client.get('/api/auth/me')
}
