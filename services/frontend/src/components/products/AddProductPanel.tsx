import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import type { AxiosError } from 'axios'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useAddProduct } from '@/hooks/useProducts'
import { addProductSchema, type AddProductSchema } from '@/schemas/product.schema'
import type { ErrorResponse } from '@/types/api.types'
import { cn } from '@/lib/utils'

interface AddProductPanelProps {
  open: boolean
  onClose: () => void
}

const URL_FIELD_ERRORS: Record<string, string> = {
  INVALID_PRODUCT_URL:
    "This doesn't look like a valid product page. Check the URL and try again.",
  DUPLICATE_PRODUCT: "You're already tracking this product.",
  SCRAPING_FAILED:
    "We couldn't fetch the price for this product. Try a different URL.",
}

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(
    () => window.matchMedia('(min-width: 1024px)').matches,
  )
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return isDesktop
}

export function AddProductPanel({ open, onClose }: AddProductPanelProps) {
  const isDesktop = useIsDesktop()
  const mutation = useAddProduct()
  const [showLimitBanner, setShowLimitBanner] = useState(false)

  const {
    register: field,
    handleSubmit,
    setError,
    setValue,
    reset,
    formState: { errors, isSubmitting, isValid },
  } = useForm<AddProductSchema>({
    resolver: zodResolver(addProductSchema),
    mode: 'onBlur',
  })

  // Clipboard paste detection on open
  useEffect(() => {
    if (!open) return
    navigator.clipboard
      .readText()
      .then((text) => {
        try {
          const parsed = new URL(text)
          if (parsed.protocol === 'https:') setValue('url', text, { shouldValidate: true })
        } catch {
          // not a URL — ignore
        }
      })
      .catch(() => {
        // clipboard unavailable — ignore
      })
  }, [open, setValue])

  // Reset form on close
  useEffect(() => {
    if (!open) {
      reset()
      setShowLimitBanner(false)
    }
  }, [open, reset])

  // Escape key closes panel
  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  async function onSubmit(values: AddProductSchema) {
    setShowLimitBanner(false)
    try {
      await mutation.mutateAsync(values.url)
      onClose()
    } catch (err) {
      const code = (err as AxiosError<ErrorResponse>).response?.data?.code
      if (code === 'PRODUCT_LIMIT_EXCEEDED') {
        setShowLimitBanner(true)
      } else if (code && code in URL_FIELD_ERRORS) {
        setError('url', { message: URL_FIELD_ERRORS[code] })
      } else {
        toast.error('Something went wrong. Please try again.')
      }
    }
  }

  const isDisabled = isSubmitting

  const panelVariants = isDesktop
    ? {
        hidden: { x: '100%' },
        visible: { x: 0, transition: { type: 'tween', duration: 0.25, ease: 'easeOut' } },
        exit: { x: '100%', transition: { type: 'tween', duration: 0.2, ease: 'easeIn' } },
      }
    : {
        hidden: { y: '100%' },
        visible: { y: 0, transition: { type: 'tween', duration: 0.25, ease: 'easeOut' } },
        exit: { y: '100%', transition: { type: 'tween', duration: 0.2, ease: 'easeIn' } },
      }

  return (
    <AnimatePresence>
      {open && (
        <div
          className="fixed inset-0 z-50"
          role="dialog"
          aria-modal="true"
          aria-label="Track a new product"
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Panel */}
          <motion.div
            className={cn(
              'absolute bg-card shadow-xl overflow-y-auto',
              isDesktop
                ? 'right-0 top-0 h-full w-[400px]'
                : 'bottom-0 left-0 right-0 rounded-t-2xl max-h-[90dvh]',
            )}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h2 className="text-base font-semibold text-foreground">Track a product</h2>
              <button
                type="button"
                aria-label="Close panel"
                onClick={onClose}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-6">
              {/* Limit exceeded banner */}
              {showLimitBanner && (
                <div
                  role="alert"
                  aria-live="polite"
                  className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
                >
                  You've reached your 5-product limit. Remove a product to add another.
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="add-product-url" className="text-sm font-medium text-slate-700">
                    Product URL
                  </label>
                  <input
                    id="add-product-url"
                    type="url"
                    // eslint-disable-next-line jsx-a11y/no-autofocus
                    autoFocus
                    autoComplete="url"
                    placeholder="https://www.amazon.com/dp/..."
                    aria-describedby={errors.url ? 'add-product-url-error' : undefined}
                    aria-invalid={errors.url ? true : undefined}
                    className={cn(
                      'h-10 w-full rounded-lg border border-input bg-white px-3 text-sm text-slate-900 placeholder:text-muted-foreground transition-colors duration-150',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
                      'disabled:pointer-events-none disabled:opacity-50',
                      errors.url && 'border-destructive focus-visible:ring-destructive',
                    )}
                    {...field('url')}
                  />
                  {errors.url && (
                    <p id="add-product-url-error" role="alert" className="text-xs text-destructive">
                      {errors.url.message}
                    </p>
                  )}
                </div>

                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={isDisabled}
                  aria-disabled={!isValid || isDisabled}
                >
                  {isSubmitting ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                      Tracking…
                    </span>
                  ) : (
                    'Track product'
                  )}
                </Button>
              </form>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}