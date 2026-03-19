import { Link } from 'react-router-dom'
import { NotificationBell } from '@/components/notifications/NotificationBell'
import { UserMenu } from '@/components/auth/UserMenu'

export function TopNav() {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background px-4">
      <Link
        to="/dashboard"
        className="flex items-center gap-2 font-bold text-foreground hover:opacity-80"
        aria-label="Dealio home"
      >
        <span className="text-primary text-lg">Dealio</span>
      </Link>

      <div className="flex items-center gap-2">
        <NotificationBell />
        <UserMenu />
      </div>
    </header>
  )
}
