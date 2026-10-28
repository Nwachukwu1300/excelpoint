import type { Transition } from 'motion/react'

// Springs tuned like easyui's motion tokens: near-critical damping, no wobble, settle in ~200-400ms.
export const spring = {
  snappy: { type: 'spring', stiffness: 380, damping: 30, mass: 0.5 },
  gentle: { type: 'spring', stiffness: 170, damping: 26, mass: 0.9 },
  morph: { type: 'spring', stiffness: 220, damping: 32, mass: 1 },
} satisfies Record<string, Transition>

export const ease = {
  soft: { duration: 0.32, ease: [0.22, 1, 0.36, 1] },
  fast: { duration: 0.2, ease: [0.2, 0, 0, 1] },
} satisfies Record<string, Transition>

/** Small pop-over (dropdowns, menus): fades and settles from just above. */
export const popover = {
  initial: { opacity: 0, y: -4, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -4, scale: 0.98, transition: { duration: 0.12 } },
  transition: ease.fast,
}

/** First-load reveal for list items: rise in 30ms apart, capped so long lists don't drag. */
export const reveal = (i: number) => ({
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const, delay: Math.min(i, 8) * 0.03 },
})
