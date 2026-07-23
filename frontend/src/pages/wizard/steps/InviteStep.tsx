import { useEffect, useState } from 'react'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

function generateInviteCode(): string {
  // Matches the server's fallback format closely enough for a friendly display code --
  // the real Adventure.invite_code is set to this exact value at Launch.
  const bytes = crypto.getRandomValues(new Uint8Array(6))
  return btoa(String.fromCharCode(...bytes)).replace(/[+/=]/g, '').slice(0, 8).toUpperCase()
}

export default function InviteStep({ data, onNext, onBack }: Props) {
  const [inviteCode, setInviteCode] = useState(data.inviteCode)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!inviteCode) setInviteCode(generateInviteCode())
  }, [])

  function copy() {
    const message = `Join my adventure "${data.campaignName}" -- invite code: ${inviteCode}`
    navigator.clipboard.writeText(message).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-zinc-400">
        Share this code with anyone you want to invite. They can join anytime, whether the
        adventure has already started or not.
      </p>

      <div className="bg-zinc-800 border border-zinc-700 rounded-2xl px-5 py-6 flex flex-col items-center gap-3">
        <span className="text-3xl font-mono font-bold tracking-[0.3em] text-accent">{inviteCode}</span>
        <button
          onClick={copy}
          className="px-4 py-1.5 text-xs font-semibold text-zinc-300 hover:text-zinc-100 border border-zinc-700 hover:border-zinc-600 rounded-lg transition-colors duration-150"
        >
          {copied ? 'Copied!' : 'Copy Invite Message'}
        </button>
      </div>

      <p className="text-xs text-zinc-600">
        You can always find and regenerate this code later from your adventure list.
      </p>

      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150">
          Back
        </button>
        <button
          onClick={() => onNext({ inviteCode })}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          Next
        </button>
      </div>
    </div>
  )
}
