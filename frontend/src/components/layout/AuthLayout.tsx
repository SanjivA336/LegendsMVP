import { Link, Outlet } from 'react-router-dom'

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-black">
      <div className="pt-10 pb-2 flex justify-center">
        <Link
          to="/"
          className="text-sm font-semibold tracking-tight text-zinc-100 hover:text-accent transition-colors duration-150"
        >
          WorldForge Engine
        </Link>
      </div>
      <Outlet />
    </div>
  )
}
