import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MarketingLayout from '../components/layout/MarketingLayout'
import AuthLayout from '../components/layout/AuthLayout'
import MenuLayout from '../components/layout/MenuLayout'
import GameplayLayout from '../components/layout/GameplayLayout'
import LandingPage from './LandingPage'
import AdventureListPage from './AdventureListPage'
import GamePage from './GamePage'
import AdventureWizard from './wizard/AdventureWizard'
import LoginPage from './LoginPage'
import SignupPage from './SignupPage'
import ProfilePage from './ProfilePage'
import PreferencesPage from './PreferencesPage'
import ProtectedRoute from '../components/auth/ProtectedRoute'
import { AuthProvider } from '../contexts/AuthContext'

const router = createBrowserRouter([
  {
    element: <MarketingLayout />,
    children: [{ path: '/', element: <LandingPage /> }],
  },
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
    ],
  },
  {
    element: (
      <ProtectedRoute>
        <MenuLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/adventures', element: <AdventureListPage /> },
      { path: '/adventures/new', element: <AdventureWizard /> },
      { path: '/profile', element: <ProfilePage /> },
      { path: '/preferences', element: <PreferencesPage /> },
    ],
  },
  {
    element: (
      <ProtectedRoute>
        <GameplayLayout />
      </ProtectedRoute>
    ),
    children: [{ path: '/adventures/:id', element: <GamePage /> }],
  },
])

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

export default function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </AuthProvider>
  )
}
