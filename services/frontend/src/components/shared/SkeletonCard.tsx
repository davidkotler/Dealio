export function SkeletonCard() {
  return (
    <div
      aria-hidden="true"
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-1 flex-col gap-1.5">
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
        </div>
        <div className="h-7 w-7 animate-pulse rounded-md bg-muted" />
      </div>
      <div className="flex items-end justify-between gap-2">
        <div className="flex flex-col gap-1.5">
          <div className="h-8 w-24 animate-pulse rounded bg-muted" />
          <div className="h-3 w-16 animate-pulse rounded bg-muted" />
        </div>
      </div>
      <div className="h-3 w-32 animate-pulse rounded bg-muted" />
    </div>
  )
}