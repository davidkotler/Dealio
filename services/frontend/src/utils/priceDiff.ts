import type { ProductResponse } from '@/types/product.types'

export function hasPriceDrop(p: ProductResponse): boolean {
  return (
    p.previous_price !== null &&
    parseFloat(p.current_price) < parseFloat(p.previous_price)
  )
}

export function calcDrop(
  curr: string,
  prev: string,
): { amount: number; percent: number } {
  const c = parseFloat(curr)
  const p = parseFloat(prev)
  return { amount: p - c, percent: ((p - c) / p) * 100 }
}