import { useState } from 'react'
import type { WizardData } from '../AdventureWizard'

interface Props {
  data: WizardData
  onNext: (patch: Pick<WizardData, 'extraCards'>) => void
  onBack: () => void
}

interface ExtraCard {
  label: string
  content: string
  keyword: string
}

export default function ExtraContextStep({ data, onNext, onBack }: Props) {
  const [cards, setCards] = useState<ExtraCard[]>(data.extraCards)

  function addCard() {
    setCards((prev) => [...prev, { label: '', content: '', keyword: '' }])
  }

  function removeCard(i: number) {
    setCards((prev) => prev.filter((_, idx) => idx !== i))
  }

  function update(i: number, field: keyof ExtraCard, value: string) {
    setCards((prev) => prev.map((c, idx) => (idx === i ? { ...c, [field]: value } : c)))
  }

  const validCards = cards.filter((c) => c.label.trim() && c.content.trim() && c.keyword.trim())

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-400">
        Optional: add context cards that are only injected when a specific keyword appears in
        the recent narrative. Useful for character backstory, secret lore, or conditional rules.
      </p>

      <div className="flex flex-col gap-3 max-h-64 overflow-y-auto pr-1">
        {cards.map((card, i) => (
          <div key={i} className="bg-zinc-800 rounded-xl p-3 flex flex-col gap-2">
            <div className="flex gap-2">
              <input
                type="text"
                value={card.label}
                onChange={(e) => update(i, 'label', e.target.value)}
                placeholder="Label"
                className="flex-1 bg-zinc-700 border border-zinc-600 text-zinc-100 placeholder-zinc-500 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
              />
              <input
                type="text"
                value={card.keyword}
                onChange={(e) => update(i, 'keyword', e.target.value)}
                placeholder="Trigger keyword"
                className="w-36 bg-zinc-700 border border-zinc-600 text-zinc-100 placeholder-zinc-500 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150"
              />
              <button
                onClick={() => removeCard(i)}
                className="text-zinc-600 hover:text-zinc-300 text-sm transition-colors duration-150"
              >
                &#x2715;
              </button>
            </div>
            <textarea
              value={card.content}
              onChange={(e) => update(i, 'content', e.target.value)}
              placeholder="Content..."
              rows={2}
              className="bg-zinc-700 border border-zinc-600 text-zinc-100 placeholder-zinc-500 px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:border-accent transition-colors duration-150 resize-none"
            />
          </div>
        ))}
      </div>

      <button
        onClick={addCard}
        className="text-sm text-accent hover:text-accent-hover transition-colors duration-150 text-left"
      >
        + Add card
      </button>

      <div className="flex justify-between pt-2">
        <button
          onClick={onBack}
          className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
        >
          Back
        </button>
        <button
          onClick={() => onNext({ extraCards: validCards })}
          className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150"
        >
          {cards.length === 0 ? 'Skip' : 'Next'}
        </button>
      </div>
    </div>
  )
}
