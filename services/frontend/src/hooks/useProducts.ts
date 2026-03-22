import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getProducts, addProduct, removeProduct } from '@/api/products.api'
import type { DashboardResponse } from '@/types/product.types'

export const DASHBOARD_QUERY_KEY = ['dashboard'] as const

export function useDashboard() {
  return useQuery<DashboardResponse>({
    queryKey: DASHBOARD_QUERY_KEY,
    queryFn: getProducts,
    refetchInterval: 30_000,
    staleTime: 20_000,
  })
}

export function useAddProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (url: string) => addProduct(url),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEY })
    },
  })
}

export function useRemoveProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => removeProduct(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: DASHBOARD_QUERY_KEY })
      const previous = queryClient.getQueryData<DashboardResponse>(DASHBOARD_QUERY_KEY)
      queryClient.setQueryData<DashboardResponse>(DASHBOARD_QUERY_KEY, (old) =>
        old ? { ...old, products: old.products.filter((p) => p.id !== id) } : old,
      )
      return { previous }
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(DASHBOARD_QUERY_KEY, ctx.previous)
      }
      toast.error('Failed to remove product.')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEY })
    },
  })
}