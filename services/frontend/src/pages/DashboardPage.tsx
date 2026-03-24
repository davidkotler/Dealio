import { useState } from 'react'
import { Plus } from 'lucide-react'
import { toast } from 'sonner'
import { useDashboard, useRemoveProduct, useAddProduct } from '@/hooks/useProducts'
import { ProductGrid } from '@/components/products/ProductGrid'
import { PlanUsageBar } from '@/components/products/PlanUsageBar'
import { EmptyProducts } from '@/components/products/EmptyProducts'
import { AddProductPanel } from '@/components/products/AddProductPanel'
import { SkeletonCard } from '@/components/shared/SkeletonCard'
import { Button } from '@/components/ui/button'
import { MAX_PRODUCTS } from '@/config/plans'
import { cn } from '@/lib/utils'

export function DashboardPage() {
  const [panelOpen, setPanelOpen] = useState(false)
  const { data: dashboard, isLoading } = useDashboard()
  const removeProduct = useRemoveProduct()
  const addProduct = useAddProduct()

  const products = dashboard?.products ?? []
  const productCount = products.length
  const isAtLimit = productCount >= MAX_PRODUCTS

  function handleRemove(id: string) {
    const product = products.find((p) => p.id === id)
    if (!product) return

    removeProduct.mutate(id, {
      onSuccess: () => {
        toast(`Stopped tracking ${product.product_name}`, {
          duration: 5000,
          action: {
            label: 'Undo',
            onClick: () => addProduct.mutate(product.url),
          },
        })
      },
    })
  }

  return (
    <>
    <AddProductPanel open={panelOpen} onClose={() => setPanelOpen(false)} />
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-bold text-foreground">Your Tracked Products</h1>
        <span
          title={isAtLimit ? 'Upgrade to track more products' : undefined}
          className="inline-block"
        >
          <Button
            disabled={isAtLimit}
            className={cn(isAtLimit && 'pointer-events-none')}
            aria-disabled={isAtLimit}
            onClick={() => setPanelOpen(true)}
          >
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Add Product
          </Button>
        </span>
      </div>

      {/* Plan usage */}
      <PlanUsageBar count={productCount} max={MAX_PRODUCTS} />

      {/* Content */}
      {isLoading ? (
        <div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          aria-busy="true"
          aria-label="Loading products"
        >
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : products.length === 0 ? (
        <EmptyProducts onAdd={() => setPanelOpen(true)} />
      ) : (
        <ProductGrid products={products} onRemove={handleRemove} />
      )}
    </div>
    </>
  )
}