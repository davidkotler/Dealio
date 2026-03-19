import client from '@/api/client'
import type { AuthUser } from '@/types/auth.types'

export interface RegisterPayload {
  email: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
}

export interface ResetPasswordPayload {
  token: string
  new_password: string
}

export async function register(payload: RegisterPayload): Promise<AuthUser> {
  const { data } = await client.post<AuthUser>('/auth/register', payload)
  return data
}

export async function login(payload: LoginPayload): Promise<AuthUser> {
  const { data } = await client.post<AuthUser>('/auth/login', payload)
  return data
}

export async function logout(): Promise<void> {
  await client.post('/auth/logout')
}

export async function googleLogin(): Promise<void> {
  window.location.href =
    import.meta.env.VITE_API_BASE_URL + '/api/v1/auth/google/login'
}

export async function requestPasswordReset(email: string): Promise<void> {
  await client.post('/auth/password-reset', { email })
}

export async function confirmPasswordReset(
  payload: ResetPasswordPayload,
): Promise<void> {
  await client.post('/auth/password-reset/confirm', payload)
}

export async function changePassword(
  payload: ChangePasswordPayload,
): Promise<void> {
  await client.put('/auth/password', payload)
}