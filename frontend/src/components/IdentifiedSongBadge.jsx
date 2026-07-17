export default function IdentifiedSongBadge({ song }) {
  if (!song?.title) return null

  return (
    <div className="identified-song-badge">
      <span>Identified:</span>
      <strong>{song.title}</strong>
      {song.artist && <span className="identified-song-artist">by {song.artist}</span>}
    </div>
  )
}
