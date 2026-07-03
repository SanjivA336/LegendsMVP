import { Outlet } from 'react-router-dom'

export default function GameplayLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-zinc-950">
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  )
}
