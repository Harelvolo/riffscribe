import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'
import Icon from './Icon'

export default function WaveformSelector({ audioUrl, onRegionChange }) {
  const containerRef = useRef(null)
  const waveSurferRef = useRef(null)
  const regionsRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)

  useEffect(() => {
    if (!audioUrl || !containerRef.current) return

    const regions = RegionsPlugin.create()
    regionsRef.current = regions

    const waveSurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#4b4b63',
      progressColor: '#8b7bff',
      cursorColor: '#f8fafc',
      height: 120,
      url: audioUrl,
      plugins: [regions],
    })
    waveSurferRef.current = waveSurfer

    waveSurfer.on('play', () => setIsPlaying(true))
    waveSurfer.on('pause', () => setIsPlaying(false))
    waveSurfer.on('finish', () => setIsPlaying(false))

    waveSurfer.on('decode', () => {
      const duration = waveSurfer.getDuration()
      const region = regions.addRegion({
        start: 0,
        end: Math.min(10, duration),
        color: 'rgba(79, 79, 214, 0.2)',
        drag: true,
        resize: true,
      })
      onRegionChange({ start: region.start, end: region.end })
    })

    regions.on('region-updated', (region) => {
      onRegionChange({ start: region.start, end: region.end })
    })

    regions.on('region-in', () => {})

    return () => {
      waveSurfer.destroy()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioUrl])

  const togglePlay = () => {
    waveSurferRef.current?.playPause()
  }

  return (
    <div className="waveform-selector">
      <div ref={containerRef} />
      <div className="waveform-controls">
        <button type="button" className="secondary-button" onClick={togglePlay}>
          <Icon name={isPlaying ? 'pause' : 'play'} size={16} />
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <p className="hint">Drag the highlighted region to mark where the solo starts and ends.</p>
      </div>
    </div>
  )
}
