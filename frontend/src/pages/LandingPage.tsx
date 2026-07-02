import { Link } from 'react-router-dom'
import { useGameStore } from '../store/gameStore'

export default function LandingPage() {
  const adventures = useGameStore((s) => s.adventures)

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-24 gap-8">
      <div className="flex flex-col items-center gap-4 text-center max-w-xl">
        <div className="text-xs uppercase tracking-wider text-zinc-400 mb-2">
          AI-Powered Tabletop Engine
        </div>
        <h1 className="text-5xl font-semibold tracking-tight text-zinc-100">
          WorldForge Engine
        </h1>
        <p className="text-zinc-400 text-lg leading-relaxed">
          A living world driven by a language model DM. Build your world, create your character,
          and step into a story that evolves with every action you take.
        </p>
      </div>

      <div className="flex items-center gap-3 mt-4">
        <Link
          to="/adventures/new"
          className="bg-accent hover:bg-accent-hover text-zinc-950 font-semibold px-5 py-2.5 rounded-lg transition-colors duration-150"
        >
          Create Adventure
        </Link>
        {adventures.length > 0 && (
          <Link
            to="/adventures"
            className="text-zinc-400 hover:text-zinc-100 px-5 py-2.5 rounded-lg border border-zinc-700 hover:border-zinc-600 transition-colors duration-150"
          >
            View Adventures
          </Link>
        )}
      </div>

      {adventures.length === 0 && (
        <p className="text-xs text-zinc-600 mt-8">No adventures yet. Create one to begin.</p>
      )}
    </div>
  )
}
