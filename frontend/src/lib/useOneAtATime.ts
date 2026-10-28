import { useRef } from 'react'

/**
 * Starts a request only if the last one has finished. A disabled button isn't enough:
 * React Query's isPending reaches the button a render late, so a fast double click sends twice.
 * `final` keeps it locked after a success, for actions that move on (a delete), where a late click is stale.
 */
export function useOneAtATime() {
  const busy = useRef(false)
  return (start: () => Promise<unknown>, { final = false } = {}) => {
    if (busy.current) return
    busy.current = true
    start().then(() => { busy.current = final }, () => { busy.current = false /* the mutation's error state shows it */ })
  }
}
