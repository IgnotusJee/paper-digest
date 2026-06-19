import axios from 'axios';

const client = axios.create({
  baseURL: '',
  withCredentials: true, // Crucial for HttpOnly session cookie
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor to handle unauthenticated 401s and redirect to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Avoid redirecting if we are already trying to log in or fetch the profile
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && !error.config.url?.includes('/api/auth/me')) {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
      }
    }
    return Promise.reject(error);
  }
);

export default client;
