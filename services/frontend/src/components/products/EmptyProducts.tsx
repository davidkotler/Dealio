import { PackageSearch } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyProductsProps {
  onAdd: () => void
}

export function EmptyProducts({ onAdd }: EmptyProductsProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <PackageSearch className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
      </div>
      <div>
        <h3 className="text-base font-semibold text-foreground">
          No products tracked yet
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Add your first product to start tracking prices.
        </p>
      </div>
      <Button onClick={onAdd}>Add your first product</Button>
    </div>
  )
}