import { useEffect, useState } from 'react'
import Icon from './Icon'
import { useAuth } from '../auth/AuthContext'
import { apiUrl } from '../api'

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatDate(isoString) {
  const date = new Date(isoString)
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export default function Library({ onSelect }) {
  const { authHeaders } = useAuth()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(apiUrl('/api/library'), { headers: authHeaders })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setEntries(Array.isArray(data) ? data : []))
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading || entries.length === 0) return null

  return (
    <div className="library fade-in">
      <h2>Your uploads</h2>
      <ul className="library-list">
        {entries.map((entry) => (
          <li key={entry.audio_id}>
            <button type="button" className="library-item" onClick={() => onSelect(entry)}>
              <span className="library-item-icon">
                <Icon name="logo" size={16} />
              </span>
              <span className="library-item-info">
                <span className="library-item-name">{entry.filename}</span>
                <span className="library-item-meta">
                  {formatDuration(entry.duration)} &middot; {formatDate(entry.uploaded_at)}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
