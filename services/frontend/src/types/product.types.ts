export interface ProductResponse {
  id: string
  url: string
  product_name: string
  current_price: string
  previous_price: string | null
  last_checked_at: string | null
  created_at: string
}

export interface DashboardResponse {
  products: ProductResponse[]
  unread_notification_count: number
}