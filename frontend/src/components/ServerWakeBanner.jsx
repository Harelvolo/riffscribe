import { useEffect, useState } from 'react'
import { apiUrl } from '../api'

const POLL_INTERVAL_MS = 3000
const HEALTH_CHECK_TIMEOUT_MS = 5000

export default function ServerWakeBanner() {
  const [isAwake, setIsAwake] = useState(null) // null = checking (no flash on the common warm case)

  useEffect(() => {
    let cancelled = false
    let interval

    const checkHealth = async () => {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT_MS)
        const res = await fetch(apiUrl('/api/health'), { signal: controller.signal })
        clearTimeout(timeoutId)
        if (res.ok) {
          if (!cancelled) setIsAwake(true)
          return true
        }
      } catch {
        // still asleep or unreachable - keep polling
      }
      if (!cancelled) setIsAwake(false)
      return false
    }

    checkHealth().then((awake) => {
      if (awake || cancelled) return
      interval = setInterval(async () => {
        const nowAwake = await checkHealth()
        if (nowAwake) clearInterval(interval)
      }, POLL_INTERVAL_MS)
    })

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  if (isAwake !== false) return null

  return (
    <div className="wake-banner">
      <span className="spinner" aria-hidden="true" />
      Waking up the server - this can take up to a minute on the free tier.
    </div>
  )
}
