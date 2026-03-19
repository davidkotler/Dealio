import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link } from 'react-router-dom'
import { AuthCard } from '@/components/auth/AuthCard'
import { Button } from '@/components/ui/button'
import { forgotPasswordSchema, type ForgotPasswordSchema } from '@/schemas/auth.schema'
import { requestPasswordReset } from '@/api/auth.api'
import { cn } from '@/lib/utils'

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)

  const {
    register: field,
    handleSubmit,
    formState: { errors, isSubmitting, isValid, submitCount },
  } = useForm<ForgotPasswordSchema>({
    resolver: zodResolver(forgotPasswordSchema),
    mode: 'onBlur',
  })

  async function onSubmit(values: ForgotPasswordSchema) {
    try {
      await requestPasswordReset(values.email)
    } catch {
      // Always show success to avoid email enumeration
    } finally {
      setSubmitted(true)
    }
  }

  const disableSubmit = (submitCount === 0 && !isValid) || isSubmitting

  if (submitted) {
    return (
      <AuthCard title="Check your inbox">
        <p className="text-sm text-muted-foreground text-center">
          If an account exists for that email, a reset link is on its way.
        </p>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to log in
          </Link>
        </p>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you a reset link"
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="forgot-email" className="text-sm font-medium text-slate-700">
            Email
          </label>
          <input
            id="forgot-email"
            type="email"
            autoComplete="email"
            aria-describedby={errors.email ? 'forgot-email-error' : undefined}
            aria-invalid={errors.email ? true : undefined}
            placeholder="you@example.com"
            className={cn(
              'h-10 rounded-lg border border-input bg-white px-3 text-sm text-slate-900 placeholder:text-muted-foreground transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
              'disabled:pointer-events-none disabled:opacity-50',
              errors.email && 'border-destructive',
            )}
            {...field('email')}
          />
          {errors.email && (
            <p id="forgot-email-error" role="alert" className="text-xs text-destructive">
              {errors.email.message}
            </p>
          )}
        </div>

        <Button type="submit" size="lg" className="w-full mt-1" disabled={disableSubmit}>
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Sending…
            </span>
          ) : (
            'Send reset link'
          )}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Remembered your password?{' '}
        <Link to="/login" className="font-medium text-primary hover:underline">
          Log in
        </Link>
      </p>
    </AuthCard>
  )
}
