import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listNotifications, readNotification } from '@/api/notifications.api'

export const NOTIFICATIONS_QUERY_KEY = ['notifications'] as const

export function useNotifications(limit = 20) {
  return useInfiniteQuery({
    queryKey: [...NOTIFICATIONS_QUERY_KEY, limit],
    queryFn: ({ pageParam }) =>
      listNotifications({ cursor: pageParam as string | undefined, limit }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  })
}

export function useReadNotification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => readNotification(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY })
      void queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}