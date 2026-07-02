import { useState } from 'react'
import type { WizardData } from '../AdventureWizard'

interface Props {
  data: WizardData
  onNext: (patch: Pick<WizardData, 'mapSize'>) => void
  onBack: () => void
}

const SIZES = [
  {
    value: 'small' as const,
    label: 'Small',
    dims: '32 × 32',
    tiles: '1,024 tiles',
    description: 'A tight, focused world. Quick to explore and ideal for shorter campaigns or solo play.',
  },
  {
    value: 'medium' as const,
    label: 'Medium',
    dims: '64 × 64',
    tiles: '4,096 tiles',
    description: 'The balanced choice. Enough room for diverse biomes, multiple regions, and a full story arc.',
  },
  {
    value: 'large' as const,
    label: 'Large',
    dims: '128 × 128',
    tiles: '16,384 tiles',
    description: 'A sprawling continent. Best for long campaigns and groups who want to get lost in the world.',
  },
]

export default function MapSizeStep({ data, onNext, onBack }: Props) {
  const [selected, setSelected] = useState<'small' | 'medium' | 'large'>(data.mapSize)

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-400">
        Choose how large your world map will be. Larger maps take a moment longer to generate.
      </p>

      <div className="flex flex-col gap-3">
        {SIZES.map((size) => {
          const active = selected === size.value
          return (
            <button
              key={size.value}
              onClick={() => setSelected(size.value)}
              className={`w-full text-left rounded-2xl border px-4 py-4 transition-colors duration-150 ${
                active
                  ? 'border-accent bg-zinc-800/80'
                  : 'border-zinc-700 bg-zinc-800/40 hover:border-zinc-600'
              }`}
            >
              <div className="flex items-baseline gap-3 mb-1">
                <span className="text-sm font-semibold text-zinc-100">{size.label}</span>
                <span className="text-xs font-mono text-zinc-400">{size.dims}</span>
                <span className="text-xs text-zinc-600 ml-auto">{size.tiles}</span>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">{size.description}</p>
            </button>
          )
        })}
      </div>

      <div className="flex justify-between pt-2">
        <button
          onClick={onBack}
          className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          Back
        </button>
        <button
          onClick={() => onNext({ mapSize: selected })}
          className="px-5 py-2 rounded-xl bg-accent text-sm font-semibold text-zinc-950 hover:bg-accent/90 transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  )
}
