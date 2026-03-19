import axios, { type AxiosError } from 'axios'
import { useAuthStore } from '@/store/auth.store'
import type { ErrorResponse } from '@/types/api.types'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL + '/api/v1',
  withCredentials: true,
})

client.interceptors.response.use(
  (r) => r,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearUser()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default client