import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

function navLinkClass({ isActive }: { isActive: boolean }) {
  return `text-sm transition-colors duration-150 ${
    isActive ? 'text-zinc-100 font-medium' : 'text-zinc-400 hover:text-zinc-100'
  }`
}

export default function Navbar() {
  const { signOut } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await signOut()
    navigate('/login')
  }

  return (
    <nav className="h-12 border-b border-zinc-800 flex items-center px-6 gap-6 shrink-0">
      <button
        onClick={handleSignOut}
        className="text-sm text-zinc-400 hover:text-red-400 transition-colors duration-150"
      >
        Sign out
      </button>
      <Link
        to="/adventures"
        className="text-sm font-semibold tracking-tight text-zinc-100 hover:text-accent transition-colors duration-150"
      >
        WorldForge Engine
      </Link>
      <div className="flex-1" />
      <NavLink to="/adventures" className={navLinkClass}>
        Adventures
      </NavLink>
      <NavLink to="/preferences" className={navLinkClass}>
        Preferences
      </NavLink>
      <NavLink to="/profile" className={navLinkClass}>
        Profile
      </NavLink>
    </nav>
  )
}
