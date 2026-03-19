import { Navigate, Route, Routes } from 'react-router-dom'
import { PrivateRoute } from '@/routes/PrivateRoute'
import { PublicOnlyRoute } from '@/routes/PublicOnlyRoute'
import { AppShell } from '@/routes/AppShell'
import { LandingPage } from '@/pages/LandingPage'
import { SignUpPage } from '@/pages/SignUpPage'
import { LoginPage } from '@/pages/LoginPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'

function App() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>
      <Route element={<PrivateRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
          <Route path="/products/:id" element={<div>ProductDetail</div>} />
          <Route path="/notifications" element={<div>Notifications</div>} />
          <Route path="/settings" element={<div>Settings</div>} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
