import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Link2, Eye, Bell } from 'lucide-react'

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (delay: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut', delay },
  }),
}

const STEPS = [
  {
    icon: Link2,
    title: 'Add a URL',
    description: 'Paste any product link from any store.',
  },
  {
    icon: Eye,
    title: 'We watch it',
    description: 'We check the price automatically, around the clock.',
  },
  {
    icon: Bell,
    title: 'Get notified',
    description: 'You get an alert the moment the price drops.',
  },
]

export function LandingPage() {
  const googleLoginUrl =
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''

  return (
    <div className="min-h-dvh bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="w-full px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <span className="text-xl font-bold text-slate-900 tracking-tight">
          Dealio
        </span>
        <Link
          to="/login"
          className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
        >
          Log In
        </Link>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col">
        {/* Hero Section */}
        <section className="flex flex-col items-center text-center px-6 pt-16 pb-20 max-w-3xl mx-auto w-full">
          <motion.h1
            className="text-3xl sm:text-4xl font-bold text-slate-900 leading-tight"
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={0}
          >
            Track prices. Get notified. Never overpay.
          </motion.h1>

          <motion.p
            className="mt-4 text-lg text-slate-600 max-w-xl leading-relaxed"
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={0.1}
          >
            Paste any product URL and we'll alert you the moment the price
            drops.
          </motion.p>

          <motion.div
            className="mt-8 flex flex-col sm:flex-row items-center gap-3"
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={0.2}
          >
            <Link
              to="/signup"
              className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-primary text-primary-foreground text-base font-semibold hover:bg-primary/90 transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 active:scale-[0.98]"
            >
              Get Started Free
            </Link>

            <button
              type="button"
              onClick={() => {
                window.location.href =
                  googleLoginUrl + '/api/v1/auth/google/login'
              }}
              className="inline-flex items-center gap-2 h-12 px-6 rounded-lg border border-slate-200 bg-white text-slate-700 text-sm font-semibold hover:bg-slate-50 transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
            >
              <svg
                className="w-4 h-4 shrink-0"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
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
              Sign in with Google
            </button>
          </motion.div>
        </section>

        {/* How It Works Section */}
        <section className="px-6 pb-20 max-w-5xl mx-auto w-full">
          <motion.h2
            className="text-2xl font-bold text-slate-900 text-center mb-10"
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-60px' }}
            custom={0}
          >
            How it works
          </motion.h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {STEPS.map((step, i) => {
              const Icon = step.icon
              return (
                <motion.div
                  key={step.title}
                  className="bg-white rounded-xl shadow-sm p-6 flex flex-col items-start gap-4"
                  variants={fadeUp}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, margin: '-60px' }}
                  custom={i * 0.1}
                >
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-primary" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900 mb-1">
                      {step.title}
                    </h3>
                    <p className="text-sm text-slate-600 leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-200 py-6 px-6 text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link
          to="/login"
          className="font-medium text-primary hover:text-primary/80 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
        >
          Log In
        </Link>
      </footer>
    </div>
  )
}
