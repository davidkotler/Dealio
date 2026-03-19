import { Bell } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import type { DashboardResponse } from '@/types/product.types'

export function NotificationBell() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const dashboard = qc.getQueryData<DashboardResponse>(['dashboard'])
  const unreadCount = dashboard?.unread_notification_count ?? 0

  const badgeLabel =
    unreadCount === 0 ? null : unreadCount > 9 ? '9+' : String(unreadCount)

  const ariaLabel =
    unreadCount === 0
      ? 'Notifications'
      : `Notifications, ${unreadCount} unread`

  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={() => navigate('/notifications')}
      className={cn(
        'relative inline-flex h-9 w-9 items-center justify-center rounded-lg',
        'text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      )}
    >
      <Bell className="h-5 w-5" />
      {badgeLabel && (
        <span
          aria-hidden="true"
          className={cn(
            'absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center',
            'rounded-full bg-primary px-1 text-[10px] font-semibold leading-none text-primary-foreground',
          )}
        >
          {badgeLabel}
        </span>
      )}
    </button>
  )
}
