import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { apiUrl } from '../api'

const CLIENT_ID_KEY = 'riffscribe_client_id'
const PING_INTERVAL_MS = 30000
const ADMIN_EMAIL = 'harelvolo1@gmail.com'

function getClientId() {
  let id = localStorage.getItem(CLIENT_ID_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(CLIENT_ID_KEY, id)
  }
  return id
}

export default function StatsWidget() {
  const { session } = useAuth()
  const isAdmin = session?.profile?.email === ADMIN_EMAIL
  const [stats, setStats] = useState(null)

  // The heartbeat/fetch always runs (for every visitor, admin or not) so the
  // "online now" count stays accurate - only the visible UI below is
  // restricted to the admin account.
  useEffect(() => {
    const clientId = getClientId()

    const ping = () => {
      fetch(apiUrl('/api/presence/ping'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: clientId }),
      }).catch(() => {})
    }

    const fetchStats = () => {
      fetch(apiUrl('/api/stats'))
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => data && setStats(data))
        .catch(() => {})
    }

    ping()
    fetchStats()
    const interval = setInterval(() => {
      ping()
      fetchStats()
    }, PING_INTERVAL_MS)

    return () => clearInterval(interval)
  }, [])

  if (!isAdmin || !stats) return null

  return (
    <div className="stats-widget">
      <span>{stats.total_users.toLocaleString()} registered</span>
      <span className="stats-dot">&middot;</span>
      <span>{stats.online_now.toLocaleString()} online now</span>
    </div>
  )
}
