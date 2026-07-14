const GLYPHS = ['♪', '♫', '♬', '♪', '♫']

// Fixed, hand-picked layout so it's stable across renders (no per-render randomness).
const NOTES = [
  { glyph: 0, left: '3%', size: 48, duration: 26, delay: -2 },
  { glyph: 1, left: '11%', size: 34, duration: 34, delay: -14 },
  { glyph: 2, left: '19%', size: 60, duration: 22, delay: -8 },
  { glyph: 3, left: '8%', size: 30, duration: 40, delay: -24 },
  { glyph: 4, left: '16%', size: 40, duration: 30, delay: -5 },
  { glyph: 0, left: '84%', size: 44, duration: 28, delay: -10 },
  { glyph: 1, left: '91%', size: 56, duration: 24, delay: -3 },
  { glyph: 2, left: '79%', size: 32, duration: 36, delay: -18 },
  { glyph: 3, left: '95%', size: 38, duration: 32, delay: -22 },
  { glyph: 4, left: '87%', size: 28, duration: 42, delay: -30 },
]

export default function AmbientBackground() {
  return (
    <div className="ambient-background" aria-hidden="true">
      {NOTES.map((note, i) => (
        <span
          key={i}
          className="ambient-note"
          style={{
            left: note.left,
            fontSize: note.size,
            animationDuration: `${note.duration}s`,
            animationDelay: `${note.delay}s`,
          }}
        >
          {GLYPHS[note.glyph]}
        </span>
      ))}
    </div>
  )
}
