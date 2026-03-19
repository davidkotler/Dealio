import { useRef, useState } from 'react'
import { Settings, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth.store'
import { logout } from '@/api/auth.api'

export function UserMenu() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const clearUser = useAuthStore((s) => s.clearUser)
  const triggerRef = useRef<HTMLButtonElement>(null)

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') {
      setOpen(false)
      triggerRef.current?.focus()
    }
  }

  async function handleLogout() {
    setOpen(false)
    try {
      await logout()
    } finally {
      clearUser()
      qc.clear()
      navigate('/login')
    }
  }

  const initials = user?.email?.charAt(0).toUpperCase() ?? '?'

  return (
    <div className="relative" onKeyDown={handleKeyDown}>
      <button
        ref={triggerRef}
        type="button"
        aria-label="Account menu"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'inline-flex h-8 w-8 items-center justify-center rounded-full',
          'bg-primary text-primary-foreground text-sm font-semibold',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'transition-opacity hover:opacity-90',
        )}
      >
        {initials}
      </button>

      {open && (
        <>
          {/* Backdrop to close on outside click */}
          <div
            className="fixed inset-0 z-40"
            aria-hidden="true"
            onClick={() => setOpen(false)}
          />
          <div
            role="menu"
            className={cn(
              'absolute right-0 top-10 z-50 w-52 rounded-lg border border-border',
              'bg-popover text-popover-foreground shadow-lg',
            )}
          >
            {/* Email label */}
            <div className="border-b border-border px-3 py-2">
              <p className="truncate text-xs text-muted-foreground">
                {user?.email}
              </p>
            </div>

            <div className="py-1">
              <button
                role="menuitem"
                type="button"
                onClick={() => {
                  setOpen(false)
                  navigate('/settings')
                }}
                className={cn(
                  'flex w-full items-center gap-2 px-3 py-2 text-sm',
                  'hover:bg-accent hover:text-accent-foreground',
                  'focus-visible:bg-accent focus-visible:text-accent-foreground focus-visible:outline-none',
                )}
              >
                <Settings className="h-4 w-4" />
                Settings
              </button>

              <button
                role="menuitem"
                type="button"
                onClick={() => void handleLogout()}
                className={cn(
                  'flex w-full items-center gap-2 px-3 py-2 text-sm',
                  'text-destructive hover:bg-destructive/10',
                  'focus-visible:bg-destructive/10 focus-visible:outline-none',
                )}
              >
                <LogOut className="h-4 w-4" />
                Log Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
