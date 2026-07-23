import { useState } from 'react'
import { DndContext } from '@dnd-kit/core'
import { useDraggable, useDroppable } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import type { WizardData } from '../wizardData'

interface Props {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}

const STAT_KEYS = ['strength', 'dexterity', 'intelligence', 'fortitude', 'charisma', 'reflex'] as const

function abbrev(name: string): string {
  return name.slice(0, 3).toUpperCase()
}

function roll4d6DropLowest(): number {
  const rolls = Array.from({ length: 4 }, () => Math.floor(Math.random() * 6) + 1)
  return rolls.reduce((sum, r) => sum + r, 0) - Math.min(...rolls)
}

function generateRolls(): number[] {
  return Array.from({ length: 6 }, roll4d6DropLowest)
}

interface DraggableValueProps {
  id: string
  value: number
  disabled: boolean
}

function DraggableValue({ id, value, disabled }: DraggableValueProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id, disabled })
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`w-12 h-12 rounded-xl flex items-center justify-center font-mono font-bold text-lg cursor-grab select-none transition-all duration-150 ${
        disabled
          ? 'opacity-30 cursor-not-allowed bg-zinc-800 text-zinc-600'
          : isDragging
            ? 'bg-accent text-zinc-950 scale-110 shadow-lg z-50'
            : 'bg-zinc-700 text-zinc-100 hover:bg-zinc-600 active:scale-95'
      }`}
    >
      {value}
    </div>
  )
}

interface DroppableStatProps {
  stat: string
  label: string
  assignedValue: number | null
  onClear: () => void
}

function DroppableStat({ stat, label, assignedValue, onClear }: DroppableStatProps) {
  const { setNodeRef, isOver } = useDroppable({ id: `stat-${stat}` })
  return (
    <div
      ref={setNodeRef}
      className={`flex items-center gap-3 p-2.5 rounded-xl border transition-all duration-150 ${
        isOver
          ? 'border-accent bg-accent/10'
          : assignedValue !== null
            ? 'border-zinc-600 bg-zinc-800'
            : 'border-zinc-700 border-dashed'
      }`}
    >
      <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider w-8" title={label}>
        {abbrev(label)}
      </span>
      <div className="flex-1 h-8 flex items-center">
        {assignedValue !== null ? (
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-zinc-100">{assignedValue}</span>
            <span className="text-xs text-zinc-500 font-mono">
              ({assignedValue >= 10 ? '+' : ''}{Math.floor((assignedValue - 10) / 2)})
            </span>
            <button
              onClick={onClear}
              className="text-zinc-600 hover:text-zinc-300 text-xs transition-colors duration-150"
            >
              &#x2715;
            </button>
          </div>
        ) : (
          <span className="text-xs text-zinc-600">Drop here</span>
        )}
      </div>
    </div>
  )
}

export default function StatRollStep({ data, onNext, onBack }: Props) {
  const [rolls, setRolls] = useState<number[]>(
    data.rolledStats.length === 6 ? data.rolledStats : generateRolls()
  )
  const [assignments, setAssignments] = useState<Partial<Record<string, number>>>(data.statAssignments)
  const [usedIndices, setUsedIndices] = useState<Set<number>>(() => {
    const used = new Set<number>()
    for (const val of Object.values(data.statAssignments)) {
      const idx = rolls.indexOf(val as number)
      if (idx !== -1) used.add(idx)
    }
    return used
  })

  function reroll() {
    const newRolls = generateRolls()
    setRolls(newRolls)
    setAssignments({})
    setUsedIndices(new Set())
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over) return
    const idStr = active.id.toString()
    if (!idStr.startsWith('roll-')) return
    const rollIdx = parseInt(idStr.replace('roll-', ''))
    const overStr = over.id.toString()
    if (!overStr.startsWith('stat-')) return
    const stat = overStr.replace('stat-', '')

    // Find if this stat already has a value — return it to pool
    const prevVal = assignments[stat]
    const prevIdx = prevVal !== undefined ? rolls.indexOf(prevVal) : -1

    setAssignments((prev) => ({ ...prev, [stat]: rolls[rollIdx] }))
    setUsedIndices((prev) => {
      const next = new Set(prev)
      next.add(rollIdx)
      if (prevIdx !== -1 && prevIdx !== rollIdx) next.delete(prevIdx)
      return next
    })
  }

  function clearStat(stat: string) {
    const val = assignments[stat]
    const idx = val !== undefined ? rolls.indexOf(val) : -1
    setAssignments((prev) => {
      const next = { ...prev }
      delete next[stat]
      return next
    })
    if (idx !== -1) {
      setUsedIndices((prev) => {
        const next = new Set(prev)
        next.delete(idx)
        return next
      })
    }
  }

  const allAssigned = STAT_KEYS.every((k) => assignments[k] !== undefined)

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <p className="text-sm text-zinc-400">
            Drag rolled values onto stat slots.
          </p>
          <button
            onClick={reroll}
            className="text-sm text-accent hover:text-accent-hover transition-colors duration-150"
          >
            Reroll All
          </button>
        </div>

        {/* Rolled values pool */}
        <div className="flex gap-2 flex-wrap">
          {rolls.map((val, i) => (
            <DraggableValue
              key={i}
              id={`roll-${i}`}
              value={val}
              disabled={usedIndices.has(i)}
            />
          ))}
        </div>

        {/* Stat slots */}
        <div className="grid grid-cols-2 gap-2">
          {STAT_KEYS.map((stat) => (
            <DroppableStat
              key={stat}
              stat={stat}
              label={data.attributeNames[stat] ?? stat}
              assignedValue={assignments[stat] ?? null}
              onClear={() => clearStat(stat)}
            />
          ))}
        </div>

        <div className="flex justify-between pt-2">
          <button
            onClick={onBack}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
          >
            Back
          </button>
          <button
            onClick={() => onNext({ rolledStats: rolls, statAssignments: assignments as Record<string, number> })}
            disabled={!allAssigned}
            className="px-5 py-2 bg-accent hover:bg-accent-hover text-zinc-950 font-semibold rounded-xl transition-colors duration-150 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </DndContext>
  )
}
