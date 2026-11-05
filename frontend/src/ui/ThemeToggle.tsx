import { useTheme } from '../lib/theme'
import { Icon } from './Icon'

/** Light/dark switch, shared by the app's top bar and the public landing page. Plain CSS motion, so the
 * public pages don't need the animation library. */
export function ThemeToggle() {
  const { resolved, setTheme } = useTheme()
  const dark = resolved === 'dark'
  return (
    <button
      type="button"
      className="icon-button"
      aria-label={dark ? 'Use light theme' : 'Use dark theme'}
      title={dark ? 'Use light theme' : 'Use dark theme'}
      onClick={() => setTheme(dark ? 'light' : 'dark')}
    >
      <span key={resolved} className="theme-icon"><Icon name={dark ? 'sun' : 'moon'} /></span>
    </button>
  )
}
