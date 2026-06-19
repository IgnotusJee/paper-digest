import axios from 'axios'
import router from '@/router'

const client = axios.create({
  baseURL: '',
  withCredentials: true,
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && router.currentRoute.value.path !== '/login') {
      router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    return Promise.reject(err)
  },
)

export default client
