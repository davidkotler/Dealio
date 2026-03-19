import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import type { AxiosError } from 'axios'
import { AuthCard } from '@/components/auth/AuthCard'
import { PasswordInput } from '@/components/auth/PasswordInput'
import { Button } from '@/components/ui/button'
import { signUpSchema, type SignUpSchema } from '@/schemas/auth.schema'
import { register, googleLogin } from '@/api/auth.api'
import { useAuthStore } from '@/store/auth.store'
import type { ErrorResponse } from '@/types/api.types'

export function SignUpPage() {
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)

  const {
    register: field,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isValid, submitCount },
  } = useForm<SignUpSchema>({
    resolver: zodResolver(signUpSchema),
    mode: 'onBlur',
  })

  async function onSubmit(values: SignUpSchema) {
    try {
      const user = await register({ email: values.email, password: values.password })
      setUser({ id: user.id, email: user.email })
      toast.success('Welcome to Dealio!')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const code = (err as AxiosError<ErrorResponse>).response?.data?.code
      if (code === 'EMAIL_ALREADY_REGISTERED') {
        setError('email', {
          message: 'An account with this email already exists.',
        })
      } else if (code === 'WEAK_PASSWORD') {
        setError('password', {
          message: 'Password is too weak. Use 8+ chars, uppercase, and a number.',
        })
      } else {
        toast.error('Something went wrong. Please try again.')
      }
    }
  }

  const disableSubmit = (submitCount === 0 && !isValid) || isSubmitting

  return (
    <AuthCard title="Create your account" subtitle="Start tracking prices for free">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        {/* Email */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="signup-email" className="text-sm font-medium text-slate-700">
            Email
          </label>
          <input
            id="signup-email"
            type="email"
            autoComplete="email"
            aria-describedby={errors.email ? 'signup-email-error' : undefined}
            aria-invalid={errors.email ? true : undefined}
            placeholder="you@example.com"
            className="h-10 rounded-lg border border-input bg-white px-3 text-sm text-slate-900 placeholder:text-muted-foreground transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 aria-[invalid=true]:border-destructive"
            {...field('email')}
          />
          {errors.email && (
            <p id="signup-email-error" role="alert" className="text-xs text-destructive">
              {errors.email.message}
              {errors.email.message === 'An account with this email already exists.' && (
                <>
                  {' '}
                  <Link to="/login" className="underline hover:text-destructive/80">
                    Log in instead?
                  </Link>
                </>
              )}
            </p>
          )}
        </div>

        {/* Password */}
        <PasswordInput
          label="Password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...field('password')}
        />

        {/* Confirm Password */}
        <PasswordInput
          label="Confirm Password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          {...field('confirmPassword')}
        />

        <Button type="submit" size="lg" className="w-full mt-1" disabled={disableSubmit}>
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Creating account…
            </span>
          ) : (
            'Create account'
          )}
        </Button>
      </form>

      {/* Divider */}
      <div className="my-4 flex items-center gap-3">
        <div className="flex-1 h-px bg-slate-200" />
        <span className="text-xs text-muted-foreground">or</span>
        <div className="flex-1 h-px bg-slate-200" />
      </div>

      {/* Google */}
      <Button
        type="button"
        variant="outline"
        size="lg"
        className="w-full"
        onClick={googleLogin}
      >
        <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" aria-hidden>
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
          />
        </svg>
        Continue with Google
      </Button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-primary hover:underline">
          Log in
        </Link>
      </p>
    </AuthCard>
  )
}
