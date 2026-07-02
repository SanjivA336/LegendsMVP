import Modal from '../ui/Modal'
import HPBar from '../ui/HPBar'
import StatBlock from './StatBlock'
import type { Character } from '../../types/character'

interface CharacterDossierProps {
  character: Character | null
  open: boolean
  onClose: () => void
  accentColor: string
}

export default function CharacterDossier({
  character,
  open,
  onClose,
  accentColor,
}: CharacterDossierProps) {
  if (!character) return null

  return (
    <Modal open={open} onClose={onClose} title={character.name}>
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center font-semibold text-zinc-950 text-base shrink-0"
            style={{ backgroundColor: accentColor }}
          >
            {character.name[0]?.toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-zinc-100">{character.name}</span>
              {!character.is_player && (
                <span className="text-xs uppercase tracking-wider text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-lg">
                  NPC
                </span>
              )}
            </div>
            <HPBar hp={character.hp} maxHp={character.max_hp} />
            <div className="text-xs text-zinc-500 mt-0.5 font-mono">
              {character.hp} / {character.max_hp} HP
            </div>
          </div>
        </div>

        {character.description && (
          <p className="text-sm text-zinc-400 leading-relaxed">{character.description}</p>
        )}

        <div>
          <div className="text-xs uppercase tracking-wider text-zinc-400 mb-2">Stats</div>
          <StatBlock stats={character.stats} />
        </div>

        {character.tone && (
          <div>
            <div className="text-xs uppercase tracking-wider text-zinc-400 mb-1">Tone</div>
            <p className="text-sm text-zinc-400 italic">{character.tone}</p>
          </div>
        )}
      </div>
    </Modal>
  )
}
