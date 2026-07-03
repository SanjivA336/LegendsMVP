import { Link, Outlet, useLocation } from 'react-router-dom'

export default function AppLayout() {
  const location = useLocation()
  const isGame = location.pathname.startsWith('/adventures/') && location.pathname !== '/adventures/new'

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950">
      {!isGame && (
        <nav className="h-12 border-b border-zinc-800 flex items-center px-6 gap-6 shrink-0">
          <Link
            to="/"
            className="text-sm font-semibold tracking-tight text-zinc-100 hover:text-accent transition-colors duration-150"
          >
            WorldForge Engine
          </Link>
          <div className="flex-1" />
          <Link
            to="/adventures"
            className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
          >
            Adventures
          </Link>
          <Link
            to="/adventures/new"
            className="text-sm bg-accent hover:bg-accent-hover text-zinc-950 font-semibold px-3 py-1.5 rounded-lg transition-colors duration-150"
          >
            New Adventure
          </Link>
        </nav>
      )}
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  )
}
