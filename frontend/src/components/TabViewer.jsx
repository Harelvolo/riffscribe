import { useEffect, useRef, useState } from 'react'
import * as alphaTab from '@coderline/alphatab'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import Icon from './Icon'
import SignInButton from './SignInButton'
import { useAuth } from '../auth/AuthContext'

const INSTRUMENTS = {
  classical: { label: 'Classical', program: 24 },
  electric: { label: 'Electric', program: 29 },
}

const NOTE_TOKEN_PATTERN = /(\d+)\.(\d+)(\{[^}]*\})?/g

function withInstrument(alphatex, program) {
  return alphatex.replace(/\\instrument \d+/, `\\instrument ${program}`)
}

function extractNoteTokens(alphatex) {
  const notes = []
  let match
  NOTE_TOKEN_PATTERN.lastIndex = 0
  while ((match = NOTE_TOKEN_PATTERN.exec(alphatex)) !== null) {
    notes.push({
      fret: parseInt(match[1], 10),
      string: parseInt(match[2], 10),
      fretStart: match.index,
      fretEnd: match.index + match[1].length,
    })
  }
  return notes
}

function replaceFretAt(alphatex, fretStart, fretEnd, newFret) {
  return `${alphatex.slice(0, fretStart)}${newFret}${alphatex.slice(fretEnd)}`
}

export default function TabViewer({ alphatex }) {
  const { session } = useAuth()
  const isLocked = !session

  const containerRef = useRef(null)
  const apiRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [instrument, setInstrument] = useState('classical')
  const [editableAlphatex, setEditableAlphatex] = useState(alphatex)
  const [showEditor, setShowEditor] = useState(false)
  const [isLooping, setIsLooping] = useState(false)
  const [speed, setSpeed] = useState(1)

  useEffect(() => {
    setEditableAlphatex(alphatex)
  }, [alphatex])

  useEffect(() => {
    if (!containerRef.current) return

    const api = new alphaTab.AlphaTabApi(containerRef.current, {
      core: {
        engine: 'svg',
        fontDirectory: '/font/',
        enableLazyLoading: false,
        useWorkers: false,
      },
      display: {
        staveProfile: 'Tab',
        resources: {
          staffLineColor: '#7a7a8c',
          barSeparatorColor: '#a89a6a',
          mainGlyphColor: '#f5f0e6',
          secondaryGlyphColor: 'rgba(245,240,230,0.6)',
          scoreInfoColor: '#f5f0e6',
          barNumberColor: '#e0b84c',
        },
      },
      player: {
        enablePlayer: true,
        enableCursor: true,
        soundFont: '/soundfont/GeneralUser.sf2',
      },
    })
    apiRef.current = api

    api.playerStateChanged.on((e) => {
      setIsPlaying(e.state === alphaTab.synth.PlayerState.Playing)
    })

    api.error.on((error) => {
      console.error('AlphaTab error', error)
    })

    api.renderFinished.on(() => {
      const surface = containerRef.current
      if (!surface) return
      surface.querySelectorAll('text').forEach((node) => {
        if (node.textContent?.trim() === 'rendered by alphaTab') {
          node.style.display = 'none'
        }
      })
    })

    return () => {
      api.destroy()
    }
  }, [])

  useEffect(() => {
    if (apiRef.current && editableAlphatex) {
      apiRef.current.tex(withInstrument(editableAlphatex, INSTRUMENTS[instrument].program))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editableAlphatex, instrument])

  const togglePlay = () => {
    if (isLocked) return
    apiRef.current?.playPause()
  }

  const toggleLoop = () => {
    if (isLocked || !apiRef.current) return
    const next = !isLooping
    apiRef.current.isLooping = next
    setIsLooping(next)
  }

  const changeSpeed = (value) => {
    if (isLocked || !apiRef.current) return
    setSpeed(value)
    apiRef.current.playbackSpeed = value
  }

  const handleFretChange = (note, rawValue) => {
    const newFret = Math.max(0, Math.min(24, parseInt(rawValue, 10) || 0))
    setEditableAlphatex((current) => replaceFretAt(current, note.fretStart, note.fretEnd, newFret))
  }

  const downloadPdf = async () => {
    if (isLocked) return
    const element = containerRef.current
    if (!element) return

    setIsExporting(true)
    element.classList.add('pdf-export-mode')
    await new Promise((resolve) => requestAnimationFrame(resolve))

    try {
      const canvas = await html2canvas(element, {
        backgroundColor: '#ffffff',
        scale: 2,
        useCORS: true,
      })
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({
        orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height],
      })
      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height)
      pdf.save('guitar-solo-tab.pdf')
    } catch (err) {
      console.error('PDF export failed', err)
    } finally {
      element.classList.remove('pdf-export-mode')
      setIsExporting(false)
    }
  }

  const noteTokens = showEditor ? extractNoteTokens(editableAlphatex) : []

  return (
    <div className="tab-viewer">
      <div className="tab-viewer-controls">
        <button type="button" className="primary-button" onClick={togglePlay} disabled={isLocked}>
          <Icon name={isPlaying ? 'pause' : 'play'} size={16} />
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <div className="instrument-toggle" role="group" aria-label="Guitar tone">
          {Object.entries(INSTRUMENTS).map(([key, { label }]) => (
            <button
              key={key}
              type="button"
              className={`instrument-option ${instrument === key ? 'active' : ''}`}
              onClick={() => setInstrument(key)}
              disabled={isLocked}
            >
              {label}
            </button>
          ))}
        </div>

        <button
          type="button"
          className={`secondary-button ${isLooping ? 'active-toggle' : ''}`}
          onClick={toggleLoop}
          disabled={isLocked}
        >
          <Icon name="refresh" size={16} />
          Loop
        </button>

        <label className="speed-control">
          <span>Speed {Math.round(speed * 100)}%</span>
          <input
            type="range"
            min="0.5"
            max="1.25"
            step="0.05"
            value={speed}
            onChange={(e) => changeSpeed(parseFloat(e.target.value))}
            disabled={isLocked}
          />
        </label>

        <button
          type="button"
          className={`secondary-button ${showEditor ? 'active-toggle' : ''}`}
          onClick={() => setShowEditor((v) => !v)}
          disabled={isLocked}
        >
          <Icon name="edit" size={16} />
          {showEditor ? 'Done editing' : 'Fix a note'}
        </button>

        <button type="button" className="secondary-button" onClick={downloadPdf} disabled={isExporting || isLocked}>
          {isExporting ? <span className="spinner spinner-light" aria-hidden="true" /> : <Icon name="download" size={16} />}
          {isExporting ? 'Preparing PDF...' : 'Download PDF'}
        </button>
      </div>

      {showEditor && !isLocked && (
        <div className="note-editor fade-in">
          <p className="hint">Spot a wrong fret? Type the correct number and the tab updates instantly.</p>
          <div className="note-editor-strip">
            {noteTokens.map((note, i) => (
              <label key={`${note.fretStart}-${i}`} className="note-editor-cell">
                <span>{note.string}</span>
                <input
                  type="number"
                  min="0"
                  max="24"
                  value={note.fret}
                  onChange={(e) => handleFretChange(note, e.target.value)}
                />
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="tab-render-wrapper">
        <div ref={containerRef} className={`tab-render-surface ${isLocked ? 'blurred' : ''}`} />
        {isLocked && (
          <div className="lock-overlay">
            <span className="lock-icon">
              <Icon name="lock" size={22} />
            </span>
            <p>Sign in with Google to reveal your tab</p>
            <SignInButton />
          </div>
        )}
      </div>
    </div>
  )
}
