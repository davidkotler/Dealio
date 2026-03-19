export interface NotificationResponse {
  id: string
  tracked_product_id: string
  old_price: string
  new_price: string
  created_at: string
  read_at: string | null
}

export interface NotificationListResponse {
  notifications: NotificationResponse[]
  next_cursor: string | null
}