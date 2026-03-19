import client from '@/api/client'
import type { DashboardResponse, ProductResponse } from '@/types/product.types'

export async function getProducts(): Promise<DashboardResponse> {
  const { data } = await client.get<DashboardResponse>('/products')
  return data
}

export async function addProduct(url: string): Promise<ProductResponse> {
  const { data } = await client.post<ProductResponse>('/products', { url })
  return data
}

export async function removeProduct(id: string): Promise<void> {
  await client.delete(`/products/${id}`)
}