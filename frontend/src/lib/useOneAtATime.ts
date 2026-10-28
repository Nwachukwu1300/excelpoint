import { useRef } from 'react'

/**
 * Starts a request only if the last one has finished. A disabled button isn't enough:
 * React Query's isPending reaches the button a render late, so a fast double click sends twice.
 */
export function useOneAtATime() {
  const busy = useRef(false)
  return (start: () => Promise<unknown>) => {
    if (busy.current) return
    busy.current = true
    start().catch(() => { /* the mutation's error state shows it */ }).finally(() => { busy.current = false })
  }
}
