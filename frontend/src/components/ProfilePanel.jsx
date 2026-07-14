import { useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import Icon from './Icon'
import { apiUrl } from '../api'

export default function ProfilePanel({ onClose }) {
  const { session, authHeaders, updateProfile } = useAuth()
  const fileInputRef = useRef(null)
  const [name, setName] = useState(session.profile.name || '')
  const [bio, setBio] = useState(session.profile.bio || '')
  const [avatarPreview, setAvatarPreview] = useState(session.profile.picture || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleAvatarPick = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setAvatarPreview(URL.createObjectURL(file))
    setSaving(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(apiUrl('/api/auth/avatar'), { method: 'POST', headers: authHeaders, body: formData })
      if (!res.ok) throw new Error('Could not upload photo')
      const updated = await res.json()
      updateProfile({ picture: updated.custom_avatar_url })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('display_name', name)
      formData.append('bio', bio)
      const res = await fetch(apiUrl('/api/auth/profile'), { method: 'PATCH', headers: authHeaders, body: formData })
      if (!res.ok) throw new Error('Could not save profile')
      updateProfile({ name, bio })
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="profile-panel fade-in" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="icon-button modal-close" onClick={onClose} aria-label="Close">
          <Icon name="close" size={18} />
        </button>

        <h2>Your profile</h2>

        <button type="button" className="avatar-picker" onClick={() => fileInputRef.current?.click()}>
          {avatarPreview ? (
            <img src={avatarPreview} alt="" referrerPolicy="no-referrer" />
          ) : (
            <span className="profile-avatar-fallback">{name?.[0] ?? '?'}</span>
          )}
          <span className="avatar-picker-overlay">
            <Icon name="edit" size={16} />
          </span>
        </button>
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handleAvatarPick} hidden />

        <label className="field-label">
          Name
          <input
            type="text"
            className="text-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={60}
          />
        </label>

        <label className="field-label">
          Bio
          <textarea
            className="text-input"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={200}
            rows={3}
            placeholder="Tell us a little about yourself"
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button type="button" className="primary-button" onClick={handleSave} disabled={saving}>
          {saving ? <span className="spinner" aria-hidden="true" /> : null}
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  )
}
