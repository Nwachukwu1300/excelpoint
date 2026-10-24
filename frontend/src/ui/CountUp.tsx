import { animate, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'

/** Counts from the previous value to the new one in ~0.6s; jumps straight there with reduced motion. */
export function CountUp({ value }: { value: number }) {
  const reduce = useReducedMotion()
  const [shown, setShown] = useState(reduce ? value : 0)
  const from = useRef(reduce ? value : 0)
  useEffect(() => {
    if (reduce) { setShown(value); from.current = value; return }
    const controls = animate(from.current, value, {
      duration: 0.6,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: v => setShown(Math.round(v)),
    })
    from.current = value
    return () => controls.stop()
  }, [value, reduce])
  return <>{shown}</>
}
