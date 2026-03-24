import { AnimatePresence } from 'framer-motion'
import { ProductCard } from '@/components/products/ProductCard'
import type { ProductResponse } from '@/types/product.types'

interface ProductGridProps {
  products: ProductResponse[]
  onRemove: (id: string) => void
}

export function ProductGrid({ products, onRemove }: ProductGridProps) {
  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
      aria-label="Tracked products"
    >
      <AnimatePresence mode="popLayout">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} onRemove={onRemove} />
        ))}
      </AnimatePresence>
    </div>
  )
}