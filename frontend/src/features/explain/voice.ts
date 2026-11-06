import type { Session, Turn } from './api'

const MUTE_KEY = 'xp-voice-muted'

export function readMuted() {
  try { return localStorage.getItem(MUTE_KEY) === '1' } catch { return false }
}

export function saveMuted(muted: boolean) {
  try { localStorage.setItem(MUTE_KEY, muted ? '1' : '0') } catch { /* private mode: not remembered */ }
}

let playing: HTMLAudioElement | null = null

export function stopSpeaking() {
  playing?.pause()
  playing = null
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

/**
 * Say XP's reply. A server voice (XP_VOICE=openai) comes back as audio; the browser voice, or any failure
 * (including a browser that blocks autoplay), uses the device's own speech. Resolves false if nothing could play.
 */
export async function speak(turn: Turn, voice: Session['voice']): Promise<boolean> {
  stopSpeaking()
  if (voice === 'openai') {
    try {
      const response = await fetch(`/api/explain/turns/${turn.id}/speech/`, { credentials: 'same-origin' })
      if (response.status === 200) {
        const url = URL.createObjectURL(await response.blob())
        const audio = new Audio(url)
        audio.onended = () => URL.revokeObjectURL(url)
        playing = audio
        await audio.play()
        return true
      }
    } catch { /* falls back to the device's voice */ }
  }
  if (!('speechSynthesis' in window)) return false
  const utterance = new SpeechSynthesisUtterance(turn.reply)
  utterance.lang = 'en-GB'
  window.speechSynthesis.speak(utterance)
  return true
}
