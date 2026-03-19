import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface AuthCardProps {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
}

export function AuthCard({ title, subtitle, children, className }: AuthCardProps) {
  return (
    <div className="min-h-dvh bg-slate-50 flex flex-col items-center justify-center px-4 py-12">
      <div className={cn('w-full max-w-sm', className)}>
        {/* Logo */}
        <div className="mb-8 text-center">
          <span className="text-2xl font-bold text-slate-900 tracking-tight">
            Dealio
          </span>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm px-8 py-8">
          <div className="mb-6 text-center">
            <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
            {subtitle && (
              <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
