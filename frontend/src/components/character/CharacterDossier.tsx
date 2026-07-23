import Modal from '../ui/Modal'
import HPBar from '../ui/HPBar'
import StatBlock from './StatBlock'
import { useResolvedInstance } from '../../hooks/useEntities'
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
  // Only resolved (fetches the instance's name) when the dossier is actually open and
  // the character has one attached -- not on every party-list render.
  const { data: race } = useResolvedInstance(open ? character?.race_instance_id ?? null : null)
  const { data: characterClass } = useResolvedInstance(open ? character?.class_instance_id ?? null : null)

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

        {(character.race_instance_id || character.class_instance_id) && (
          <div className="flex gap-4 text-sm">
            {character.race_instance_id && (
              <div>
                <span className="text-xs uppercase tracking-wider text-zinc-500">Race </span>
                <span className="text-zinc-300">{race?.name ?? '…'}</span>
              </div>
            )}
            {character.class_instance_id && (
              <div>
                <span className="text-xs uppercase tracking-wider text-zinc-500">Class </span>
                <span className="text-zinc-300">{characterClass?.name ?? '…'}</span>
              </div>
            )}
          </div>
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
