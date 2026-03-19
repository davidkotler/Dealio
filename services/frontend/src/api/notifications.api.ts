import client from '@/api/client'
import type { NotificationListResponse } from '@/types/notification.types'

export interface ListNotificationsParams {
  cursor?: string
  limit?: number
}

export async function listNotifications(
  params: ListNotificationsParams = {},
): Promise<NotificationListResponse> {
  const { data } = await client.get<NotificationListResponse>(
    '/notifications',
    { params },
  )
  return data
}

export async function readNotification(id: string): Promise<void> {
  await client.post(`/notifications/${id}/read`)
}