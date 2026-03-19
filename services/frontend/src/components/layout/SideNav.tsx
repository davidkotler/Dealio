import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Bell, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useProducts } from '@/hooks/useProducts'
import { MAX_PRODUCTS } from '@/config/plans'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/notifications', label: 'Notifications', Icon: Bell },
  { to: '/settings', label: 'Settings', Icon: Settings },
] as const

export function SideNav() {
  const { data: products } = useProducts()
  const usedCount = products?.length ?? 0

  return (
    <nav
      aria-label="Sidebar navigation"
      className="hidden lg:flex w-56 shrink-0 flex-col border-r border-border bg-background"
    >
      <ul className="flex flex-col gap-1 p-3 pt-4" role="list">
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <li key={to}>
            {/* NavLink sets aria-current="page" automatically when active */}
            <NavLink
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="mt-auto p-3">
        <NavLink
          to="/settings"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <span
            className="inline-flex h-2 w-2 rounded-full bg-primary/60"
            aria-hidden="true"
          />
          <span>
            Free Plan ·{' '}
            <span className="font-medium text-foreground">
              {usedCount}/{MAX_PRODUCTS}
            </span>{' '}
            used
          </span>
        </NavLink>
      </div>
    </nav>
  )
}
