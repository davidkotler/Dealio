import { useState } from 'react'
import { motion } from 'framer-motion'
import { X, TrendingDown, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { hasPriceDrop, calcDrop } from '@/utils/priceDiff'
import { formatPrice } from '@/utils/formatPrice'
import { formatDate } from '@/utils/formatDate'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import type { ProductResponse } from '@/types/product.types'

interface ProductCardProps {
  product: ProductResponse
  onRemove: (id: string) => void
}

export function ProductCard({ product, onRemove }: ProductCardProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)

  const dropped = hasPriceDrop(product)
  const scrapeFailed = product.current_price === '0'
  const drop =
    dropped && product.previous_price
      ? calcDrop(product.current_price, product.previous_price)
      : null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.15 } }}
      transition={{ duration: 0.2 }}
      className={cn(
        'relative flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm',
        dropped && 'border-l-[3px] border-l-green-500 bg-green-50/30',
        scrapeFailed && !dropped && 'border-l-[3px] border-l-amber-400',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-foreground">
            {product.product_name}
          </h3>
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block truncate text-xs text-muted-foreground hover:text-primary hover:underline"
          >
            {new URL(product.url).hostname}
          </a>
        </div>
        <button
          type="button"
          aria-label={`Stop tracking ${product.product_name}`}
          onClick={() => setConfirmOpen(true)}
          className={cn(
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-md',
            'text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Price section */}
      {scrapeFailed ? (
        <div className="flex items-center gap-2 text-sm text-amber-600">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Couldn't fetch price</span>
        </div>
      ) : (
        <div className="flex items-end justify-between gap-2">
          <div>
            <div
              className={cn(
                'text-2xl font-bold tabular-nums',
                dropped ? 'text-green-600' : 'text-foreground',
              )}
            >
              {formatPrice(product.current_price)}
            </div>
            {product.previous_price ? (
              <div className="text-xs text-muted-foreground line-through">
                {formatPrice(product.previous_price)}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">—</div>
            )}
          </div>
          {drop && (
            <div className="flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
              <TrendingDown className="h-3 w-3" aria-hidden="true" />
              <span>
                ↓ ${drop.amount.toFixed(2)} ({drop.percent.toFixed(0)}% off)
              </span>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="text-xs text-muted-foreground">
        Checked{' '}
        {product.last_checked_at ? formatDate(product.last_checked_at) : 'Never'}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="Stop tracking?"
        description={`Remove "${product.product_name}" from your tracked products?`}
        confirmLabel="Remove"
        destructive
        onConfirm={() => {
          setConfirmOpen(false)
          onRemove(product.id)
        }}
        onCancel={() => setConfirmOpen(false)}
      />
    </motion.div>
  )
}