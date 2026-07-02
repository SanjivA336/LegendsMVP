import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppLayout from '../components/layout/AppLayout'
import LandingPage from './LandingPage'
import AdventureListPage from './AdventureListPage'
import GamePage from './GamePage'
import AdventureWizard from './wizard/AdventureWizard'
import LoginPage from './LoginPage'
import SignupPage from './SignupPage'
import ProtectedRoute from '../components/auth/ProtectedRoute'
import { AuthProvider } from '../contexts/AuthContext'

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      {
        path: '/adventures',
        element: <ProtectedRoute><AdventureListPage /></ProtectedRoute>,
      },
      {
        path: '/adventures/new',
        element: <ProtectedRoute><AdventureWizard /></ProtectedRoute>,
      },
      {
        path: '/adventures/:id',
        element: <ProtectedRoute><GamePage /></ProtectedRoute>,
      },
    ],
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
