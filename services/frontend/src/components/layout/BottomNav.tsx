import { NavLink } from 'react-router-dom'
import { Home, Bell, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', Icon: Home },
  { to: '/notifications', label: 'Notifications', Icon: Bell },
  { to: '/settings', label: 'Settings', Icon: Settings },
] as const

export function BottomNav() {
  return (
    <nav
      aria-label="Bottom navigation"
      className="fixed bottom-0 inset-x-0 z-30 flex lg:hidden border-t border-border bg-background"
    >
      {NAV_ITEMS.map(({ to, label, Icon }) => (
        /* NavLink sets aria-current="page" automatically when active */
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              'flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium transition-colors',
              isActive
                ? 'text-primary'
                : 'text-muted-foreground hover:text-foreground',
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                className={cn('h-5 w-5', isActive && 'stroke-[2.5]')}
                aria-hidden="true"
              />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}
