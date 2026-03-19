import { formatDistanceToNow } from 'date-fns'

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return formatDistanceToNow(new Date(dateStr), { addSuffix: true })
}