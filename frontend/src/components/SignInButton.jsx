import { useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../auth/AuthContext'
import { apiUrl } from '../api'

export default function SignInButton({ size = 'medium' }) {
  const { signIn } = useAuth()
  const [error, setError] = useState(null)

  const handleSuccess = async (credentialResponse) => {
    setError(null)
    try {
      const res = await fetch(apiUrl('/api/auth/google'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: credentialResponse.credential }),
      })
      if (!res.ok) throw new Error('Sign-in failed')
      const data = await res.json()
      signIn(data)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="sign-in-button">
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={() => setError('Google sign-in failed')}
        theme="filled_black"
        shape="pill"
        size={size}
        use_fedcm_for_button={false}
      />
      {error && <p className="error">{error}</p>}
    </div>
  )
}
