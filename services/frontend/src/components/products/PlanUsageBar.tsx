import { cn } from '@/lib/utils'

interface PlanUsageBarProps {
  count: number
  max: number
}

export function PlanUsageBar({ count, max }: PlanUsageBarProps) {
  const ratio = count / max
  const isRed = ratio >= 1
  const isAmber = !isRed && ratio >= 0.8

  const barColor = isRed ? 'bg-red-500' : isAmber ? 'bg-amber-500' : 'bg-primary'

  const slotsLeft = max - count
  const slotLabel = isRed
    ? 'No slots remaining'
    : isAmber
      ? `${slotsLeft} slot remaining`
      : `${slotsLeft} slots remaining`

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-foreground">
          {count}/{max} products tracked
        </span>
        <span
          className={cn(
            'text-xs',
            isRed && 'font-medium text-red-600',
            isAmber && 'font-medium text-amber-600',
            !isRed && !isAmber && 'text-muted-foreground',
          )}
        >
          {slotLabel}
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={count}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={`${count} of ${max} products tracked`}
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className={cn('h-full rounded-full transition-all duration-300', barColor)}
          style={{ width: `${Math.min((count / max) * 100, 100)}%` }}
        />
      </div>
    </div>
  )
}