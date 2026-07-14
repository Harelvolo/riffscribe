import Icon from './Icon'

const CONTENT = {
  privacy: {
    title: 'Privacy Policy',
    body: (
      <>
        <h3>What we collect</h3>
        <p>
          When you sign in with Google, we receive your name, email address, and profile picture. When you upload an
          audio file, we store that file and the tab we generate from it, tied to your account so you can revisit it
          later.
        </p>
        <h3>How we use it</h3>
        <p>
          Solely to run the service: processing your audio, generating tabs, and showing you your own library. We do
          not sell your data or share it with third parties for advertising.
        </p>
        <h3>What we store</h3>
        <p>
          Your uploaded audio, generated tabs, and profile info are stored on our server. Your browser also stores a
          session token locally so you stay signed in.
        </p>
        <h3>Your control</h3>
        <p>You can sign out at any time. To request deletion of your account and data, contact us.</p>
      </>
    ),
  },
  terms: {
    title: 'Terms of Service',
    body: (
      <>
        <h3>The service</h3>
        <p>
          Riffscribe automatically detects and transcribes guitar solos into tab notation, and can compose original
          solos. It's provided free, with a daily usage limit, and without warranty of accuracy - AI-generated
          transcriptions and compositions can and do contain mistakes.
        </p>
        <h3>Your content</h3>
        <p>
          Only upload audio you have the right to use. You're responsible for the files you upload and how you use
          any tabs or audio you generate or download.
        </p>
        <h3>Changes</h3>
        <p>
          We may change, limit, or discontinue features (including free usage limits) as the service evolves.
        </p>
      </>
    ),
  },
}

export default function LegalPanel({ topic, onClose }) {
  const content = CONTENT[topic]

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="legal-panel fade-in" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="icon-button modal-close" onClick={onClose} aria-label="Close">
          <Icon name="close" size={18} />
        </button>
        <h2>{content.title}</h2>
        <div className="legal-body">{content.body}</div>
      </div>
    </div>
  )
}
