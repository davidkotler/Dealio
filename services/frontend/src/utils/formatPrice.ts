export function formatPrice(price: string): string {
  const num = parseFloat(price)
  return `$${num.toFixed(2)}`
}