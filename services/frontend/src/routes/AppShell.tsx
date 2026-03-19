import { Outlet } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'
import { SideNav } from '@/components/layout/SideNav'
import { BottomNav } from '@/components/layout/BottomNav'

export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        {/* SideNav: visible on lg+, hidden on mobile/tablet */}
        <SideNav />
        <main className="flex-1 overflow-y-auto pb-16 lg:pb-0">
          <Outlet />
        </main>
      </div>
      {/* BottomNav: visible on mobile/tablet, hidden on lg+ */}
      <BottomNav />
    </div>
  )
}
