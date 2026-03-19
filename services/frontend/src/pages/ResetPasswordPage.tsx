import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import type { AxiosError } from 'axios'
import { AuthCard } from '@/components/auth/AuthCard'
import { PasswordInput } from '@/components/auth/PasswordInput'
import { Button } from '@/components/ui/button'
import { resetPasswordSchema, type ResetPasswordSchema } from '@/schemas/auth.schema'
import { confirmPasswordReset } from '@/api/auth.api'
import type { ErrorResponse } from '@/types/api.types'

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const {
    register: field,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isValid, submitCount },
  } = useForm<ResetPasswordSchema>({
    resolver: zodResolver(resetPasswordSchema),
    mode: 'onBlur',
  })

  async function onSubmit(values: ResetPasswordSchema) {
    try {
      await confirmPasswordReset({ token: token!, new_password: values.new_password })
      toast.success('Password updated. Please log in.')
      navigate('/login', { replace: true })
    } catch (err) {
      const code = (err as AxiosError<ErrorResponse>).response?.data?.code
      if (code === 'INVALID_RESET_TOKEN') {
        setError('root', {
          message: 'This link has expired or already been used.',
        })
      } else {
        toast.error('Something went wrong. Please try again.')
      }
    }
  }

  // Token guard — show error immediately if no token in URL
  if (!token) {
    return (
      <AuthCard title="Invalid reset link">
        <div
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive text-center"
        >
          This link has expired or already been used.{' '}
          <Link to="/forgot-password" className="underline hover:text-destructive/80">
            Request a new one →
          </Link>
        </div>
      </AuthCard>
    )
  }

  const disableSubmit = (submitCount === 0 && !isValid) || isSubmitting

  return (
    <AuthCard title="Set new password" subtitle="Enter your new password below">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        {errors.root && (
          <div
            role="alert"
            aria-live="polite"
            className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            {errors.root.message}{' '}
            <Link to="/forgot-password" className="underline hover:text-destructive/80">
              Request a new one →
            </Link>
          </div>
        )}

        <PasswordInput
          label="New Password"
          autoComplete="new-password"
          error={errors.new_password?.message}
          {...field('new_password')}
        />

        <PasswordInput
          label="Confirm Password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...field('confirm_password')}
        />

        <Button type="submit" size="lg" className="w-full mt-1" disabled={disableSubmit}>
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Updating…
            </span>
          ) : (
            'Update password'
          )}
        </Button>
      </form>
    </AuthCard>
  )
}
