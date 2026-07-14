import { useEffect, useState } from 'react'
import Icon from './Icon'

const STEPS = [
  {
    icon: 'upload',
    title: 'Upload a song',
    body: 'Upload any MP3 or WAV file that has a guitar solo in it.',
  },
  {
    icon: 'waveform',
    title: 'Mark the solo',
    body: "Drag the highlighted region on the waveform to mark exactly where the solo starts and ends. If it's a full song mix, flip the toggle so we isolate the guitar first.",
  },
  {
    icon: 'logo',
    title: 'Get your tab',
    body: 'We detect every note and turn it into a real, readable guitar tab - automatically.',
  },
  {
    icon: 'play',
    title: 'Play it back',
    body: 'Hit play to hear it with a synced cursor, in a classical or electric guitar tone.',
  },
  {
    icon: 'refresh',
    title: 'Practice tools',
    body: 'Slow the tempo down or loop a tricky section until you nail it.',
  },
  {
    icon: 'edit',
    title: 'Fix a note',
    body: 'Spot a wrong fret number? Click "Fix a note" and correct it instantly.',
  },
  {
    icon: 'user',
    title: 'Your profile',
    body: 'Add your name, a bio, and a profile photo any time from the badge up top.',
  },
]

export default function Onboarding({ onComplete }) {
  const [phase, setPhase] = useState('intro') // intro | steps | outro
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (phase !== 'outro') return
    const timer = setTimeout(onComplete, 1600)
    return () => clearTimeout(timer)
  }, [phase, onComplete])

  const handleNext = () => {
    if (stepIndex < STEPS.length - 1) {
      setStepIndex((i) => i + 1)
    } else {
      setPhase('outro')
    }
  }

  const handleBack = () => {
    if (stepIndex > 0) setStepIndex((i) => i - 1)
  }

  return (
    <div className="onboarding-backdrop">
      {phase === 'intro' && (
        <div className="onboarding-intro fade-in">
          <p className="onboarding-eyebrow">Welcome</p>
          <h1 className="onboarding-title">Riffscribe</h1>
          <button type="button" className="primary-button" onClick={() => setPhase('steps')}>
            Show me around
          </button>
          <button type="button" className="onboarding-skip" onClick={onComplete}>
            Skip
          </button>
        </div>
      )}

      {phase === 'steps' && (
        <div key={stepIndex} className="onboarding-card fade-in">
          <span className="onboarding-icon">
            <Icon name={STEPS[stepIndex].icon} size={26} />
          </span>
          <h2>{STEPS[stepIndex].title}</h2>
          <p>{STEPS[stepIndex].body}</p>

          <div className="onboarding-dots">
            {STEPS.map((_, i) => (
              <span key={i} className={`onboarding-dot ${i === stepIndex ? 'active' : ''}`} />
            ))}
          </div>

          <div className="onboarding-nav">
            {stepIndex > 0 && (
              <button type="button" className="secondary-button" onClick={handleBack}>
                Back
              </button>
            )}
            <button type="button" className="primary-button" onClick={handleNext}>
              {stepIndex < STEPS.length - 1 ? 'Next' : 'Finish'}
            </button>
          </div>
          <button type="button" className="onboarding-skip" onClick={onComplete}>
            Skip
          </button>
        </div>
      )}

      {phase === 'outro' && (
        <div className="onboarding-intro fade-in">
          <h1 className="onboarding-title">Enjoy!</h1>
        </div>
      )}
    </div>
  )
}
