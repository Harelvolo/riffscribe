import { useEffect, useState } from 'react'
import WaveformSelector from './components/WaveformSelector'
import TabViewer from './components/TabViewer'
import BackingTrackPlayer from './components/BackingTrackPlayer'
import Library from './components/Library'
import Icon from './components/Icon'
import SignInButton from './components/SignInButton'
import ProfilePanel from './components/ProfilePanel'
import LegalPanel from './components/LegalPanel'
import Onboarding from './components/Onboarding'
import AmbientBackground from './components/AmbientBackground'
import StatsWidget from './components/StatsWidget'
import ServerWakeBanner from './components/ServerWakeBanner'
import { useAuth } from './auth/AuthContext'
import { apiUrl } from './api'
import './App.css'

const STEPS = {
  UPLOAD: 'upload',
  SELECT: 'select',
  PROCESSING: 'processing',
  RESULT: 'result',
}

const MODES = {
  TRANSCRIBE: 'transcribe',
  GENERATE_OVER_TRACK: 'generate_over_track',
}

const LAST_TAB_KEY = 'gtabs_last_tab'

function App() {
  const { session, signOut, authHeaders, updateProfile } = useAuth()
  const [step, setStep] = useState(STEPS.UPLOAD)
  const [audio, setAudio] = useState(null) // { audioId, url, duration }
  const [region, setRegion] = useState({ start: 0, end: 10 })
  const [isFullMix, setIsFullMix] = useState(true)
  const [alphatex, setAlphatex] = useState(null)
  const [error, setError] = useState(null)
  const [libraryKey, setLibraryKey] = useState(0)
  const [showProfile, setShowProfile] = useState(false)
  const [legalTopic, setLegalTopic] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [mode, setMode] = useState(MODES.TRANSCRIBE)
  const [backingInstrument, setBackingInstrument] = useState('classical')
  const [mixedAudioUrl, setMixedAudioUrl] = useState(null)

  useEffect(() => {
    const cached = sessionStorage.getItem(LAST_TAB_KEY)
    if (!cached) return
    try {
      const { alphatex: cachedAlphatex, mixedAudioUrl: cachedMixedAudioUrl } = JSON.parse(cached)
      if (cachedAlphatex) {
        setAlphatex(cachedAlphatex)
        setMixedAudioUrl(cachedMixedAudioUrl ?? null)
        setStep(STEPS.RESULT)
      }
    } catch {
      sessionStorage.removeItem(LAST_TAB_KEY)
    }
  }, [])

  const handleOnboardingComplete = async () => {
    updateProfile({ has_seen_onboarding: true })
    try {
      await fetch(apiUrl('/api/auth/onboarding-complete'), { method: 'POST', headers: authHeaders })
    } catch {
      // best-effort: the local flag already keeps it from re-showing this session
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError(null)
    setMode(MODES.TRANSCRIBE)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(apiUrl('/api/upload'), { method: 'POST', headers: authHeaders, body: formData })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      setAudio({ audioId: data.audio_id, url: data.url, duration: data.duration })
      setLibraryKey((k) => k + 1)
      setStep(STEPS.SELECT)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleBackingTrackFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError(null)
    setMode(MODES.GENERATE_OVER_TRACK)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(apiUrl('/api/upload'), { method: 'POST', headers: authHeaders, body: formData })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      setAudio({ audioId: data.audio_id, url: data.url, duration: data.duration })
      setLibraryKey((k) => k + 1)
      setStep(STEPS.SELECT)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleLibrarySelect = (entry) => {
    setError(null)
    setMode(MODES.TRANSCRIBE)
    setAudio({ audioId: entry.audio_id, url: entry.url, duration: entry.duration })
    setStep(STEPS.SELECT)
  }

  const handleFindSolo = async () => {
    setStep(STEPS.PROCESSING)
    setError(null)
    try {
      const res = await fetch(apiUrl('/api/process'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          audio_id: audio.audioId,
          start: region.start,
          end: region.end,
          is_full_mix: isFullMix,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Processing failed')
      }
      const data = await res.json()
      setAlphatex(data.alphatex)
      setMixedAudioUrl(null)
      setStep(STEPS.RESULT)
      sessionStorage.setItem(LAST_TAB_KEY, JSON.stringify({ tabId: data.tab_id, alphatex: data.alphatex }))
    } catch (err) {
      setError(err.message)
      setStep(STEPS.SELECT)
    }
  }

  const handleGenerateOverTrack = async () => {
    setStep(STEPS.PROCESSING)
    setError(null)
    try {
      const res = await fetch(apiUrl('/api/generate-over-track'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          audio_id: audio.audioId,
          start: region.start,
          end: region.end,
          instrument: backingInstrument,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Generation failed')
      }
      const data = await res.json()
      setAlphatex(data.alphatex)
      setMixedAudioUrl(data.mixed_audio_url)
      setStep(STEPS.RESULT)
      sessionStorage.setItem(
        LAST_TAB_KEY,
        JSON.stringify({ tabId: data.tab_id, alphatex: data.alphatex, mixedAudioUrl: data.mixed_audio_url })
      )
    } catch (err) {
      setError(err.message)
      setStep(STEPS.SELECT)
    }
  }

  const handleGenerateRandomSolo = async () => {
    setIsGenerating(true)
    setError(null)
    try {
      const res = await fetch(apiUrl('/api/generate'), { method: 'POST', headers: authHeaders })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Generation failed')
      }
      const data = await res.json()
      setAlphatex(data.alphatex)
      setMixedAudioUrl(null)
      setStep(STEPS.RESULT)
      sessionStorage.setItem(LAST_TAB_KEY, JSON.stringify({ tabId: data.tab_id, alphatex: data.alphatex }))
    } catch (err) {
      setError(err.message)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleStartOver = () => {
    setAudio(null)
    setAlphatex(null)
    setMixedAudioUrl(null)
    setMode(MODES.TRANSCRIBE)
    setError(null)
    setStep(STEPS.UPLOAD)
    sessionStorage.removeItem(LAST_TAB_KEY)
  }

  return (
    <>
      <AmbientBackground />
      <StatsWidget />
      <ServerWakeBanner />
      <div className="app">
        {session && !session.profile.has_seen_onboarding && (
          <Onboarding onComplete={handleOnboardingComplete} />
        )}

        <header className="app-header fade-in">
          <button type="button" className="app-home-link" onClick={handleStartOver} aria-label="Back to home">
            <span className="app-logo">
              <Icon name="logo" size={24} />
            </span>
            <div className="app-header-title">
              <h1>Riffscribe</h1>
              <p className="app-subtitle">Upload a song, mark the solo, get the tab.</p>
            </div>
          </button>

          {session ? (
            <div className="profile-badge">
              <button type="button" className="profile-badge-trigger" onClick={() => setShowProfile(true)}>
                {session.profile.picture ? (
                  <img className="profile-avatar" src={session.profile.picture} alt="" referrerPolicy="no-referrer" />
                ) : (
                  <span className="profile-avatar profile-avatar-fallback">{session.profile.name?.[0] ?? '?'}</span>
                )}
                <span className="profile-name">{session.profile.name}</span>
              </button>
              <button type="button" className="icon-button sign-out-button" onClick={signOut} aria-label="Sign out">
                <Icon name="logout" size={16} />
              </button>
            </div>
          ) : (
            <SignInButton size="medium" />
          )}
        </header>

        {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}

        {step === STEPS.UPLOAD && (
          <div className="upload-panel fade-in">
            <label className="upload-dropzone">
              <input type="file" accept="audio/*" onChange={handleFileChange} />
              <span className="upload-dropzone-icon">
                <Icon name="upload" size={22} />
              </span>
              <span>Upload an MP3 or WAV with a guitar solo</span>
            </label>

            {session && <Library key={libraryKey} onSelect={handleLibrarySelect} />}

            <div className="generate-solo-panel">
              <p className="generate-solo-hint">Or let Riffscribe write you a brand new solo.</p>
              <div className="generate-solo-actions">
                <label className="secondary-button generate-solo-button">
                  <input type="file" accept="audio/*" onChange={handleBackingTrackFileChange} />
                  <Icon name="waveform" size={16} />
                  Add a backing track
                </label>
                <button
                  type="button"
                  className="secondary-button generate-solo-button"
                  onClick={handleGenerateRandomSolo}
                  disabled={isGenerating}
                >
                  {isGenerating ? <span className="spinner" aria-hidden="true" /> : <Icon name="dice" size={16} />}
                  {isGenerating ? 'Composing...' : 'Surprise me with a solo'}
                </button>
              </div>
            </div>
          </div>
        )}

        {(step === STEPS.SELECT || step === STEPS.PROCESSING) && audio && (
          <div className="select-panel fade-in">
            <WaveformSelector audioUrl={audio.url} onRegionChange={setRegion} />

            {mode === MODES.TRANSCRIBE ? (
              <label className="full-mix-toggle">
                <input
                  type="checkbox"
                  checked={isFullMix}
                  onChange={(e) => setIsFullMix(e.target.checked)}
                />
                This is a full song mix (needs instrument separation)
              </label>
            ) : (
              <div className="instrument-toggle" role="group" aria-label="Guitar tone for the new solo">
                <button
                  type="button"
                  className={`instrument-option ${backingInstrument === 'classical' ? 'active' : ''}`}
                  onClick={() => setBackingInstrument('classical')}
                >
                  Classical
                </button>
                <button
                  type="button"
                  className={`instrument-option ${backingInstrument === 'electric' ? 'active' : ''}`}
                  onClick={() => setBackingInstrument('electric')}
                >
                  Electric
                </button>
              </div>
            )}

            <p className="selection-readout">
              Selected: {region.start.toFixed(2)}s &ndash; {region.end.toFixed(2)}s
            </p>

            <button
              type="button"
              className="primary-button"
              onClick={mode === MODES.TRANSCRIBE ? handleFindSolo : handleGenerateOverTrack}
              disabled={step === STEPS.PROCESSING}
            >
              {step === STEPS.PROCESSING ? (
                <span className="spinner" aria-hidden="true" />
              ) : null}
              {step === STEPS.PROCESSING
                ? mode === MODES.TRANSCRIBE
                  ? 'Finding the solo...'
                  : 'Composing your solo...'
                : mode === MODES.TRANSCRIBE
                  ? 'Find the solo'
                  : 'Generate a solo over this'}
            </button>
          </div>
        )}

        {error && <p className="error fade-in">{error}</p>}

        {step === STEPS.RESULT && alphatex && (
          <div className="fade-in">
            {mixedAudioUrl && <BackingTrackPlayer audioUrl={mixedAudioUrl} />}
            <TabViewer alphatex={alphatex} />
            <button type="button" className="secondary-button start-over-button" onClick={handleStartOver}>
              <Icon name="refresh" size={16} />
              Start over
            </button>
          </div>
        )}

        <footer className="app-footer">
          <button type="button" className="footer-link" onClick={() => setLegalTopic('privacy')}>
            Privacy Policy
          </button>
          <span className="footer-dot">&middot;</span>
          <button type="button" className="footer-link" onClick={() => setLegalTopic('terms')}>
            Terms of Service
          </button>
        </footer>

        {legalTopic && <LegalPanel topic={legalTopic} onClose={() => setLegalTopic(null)} />}
      </div>
    </>
  )
}

export default App
