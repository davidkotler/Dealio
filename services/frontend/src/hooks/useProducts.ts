import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProducts, addProduct, removeProduct } from '@/api/products.api'

export const PRODUCTS_QUERY_KEY = ['products'] as const

export function useProducts() {
  return useQuery({
    queryKey: PRODUCTS_QUERY_KEY,
    queryFn: getProducts,
  })
}

export function useAddProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (url: string) => addProduct(url),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRODUCTS_QUERY_KEY })
    },
  })
}

export function useRemoveProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => removeProduct(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRODUCTS_QUERY_KEY })
    },
  })
}