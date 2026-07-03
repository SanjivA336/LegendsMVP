import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function MarketingLayout() {
  const { user, loading } = useAuth()

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950">
      {!loading && (
        <div className="h-12 flex items-center justify-end px-6 shrink-0">
          {user ? (
            <Link
              to="/adventures"
              className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
            >
              Adventures
            </Link>
          ) : (
            <div className="flex items-center gap-4">
              <Link
                to="/login"
                className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors duration-150"
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="text-sm bg-accent hover:bg-accent-hover text-zinc-950 font-semibold px-3 py-1.5 rounded-lg transition-colors duration-150"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      )}
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  )
}
