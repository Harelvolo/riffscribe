import Icon from './Icon'
import SignInButton from './SignInButton'
import { useAuth } from '../auth/AuthContext'

export default function BackingTrackPlayer({ audioUrl }) {
  const { session } = useAuth()
  const isLocked = !session

  return (
    <div className="backing-track-player">
      <p className="backing-track-label">Your solo, mixed with the backing track</p>
      <div className="backing-track-wrapper">
        {isLocked ? (
          <div className="lock-overlay">
            <span className="lock-icon">
              <Icon name="lock" size={22} />
            </span>
            <p>Sign in with Google to hear it with your track</p>
            <SignInButton />
          </div>
        ) : (
          <audio className="backing-track-audio" controls src={audioUrl} />
        )}
      </div>
    </div>
  )
}
