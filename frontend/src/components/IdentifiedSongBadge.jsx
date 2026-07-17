export default function IdentifiedSongBadge({ song }) {
  if (!song?.title) return null

  const label = song.source === 'melody' ? 'Sounds like:' : 'Identified:'

  return (
    <div className="identified-song-badge">
      <span>{label}</span>
      <strong>{song.title}</strong>
      {song.artist && <span className="identified-song-artist">by {song.artist}</span>}
    </div>
  )
}
