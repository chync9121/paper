import type { PropsWithChildren } from 'react'
import clsx from 'clsx'

interface PanelProps extends PropsWithChildren {
  title?: string
  subtitle?: string
  className?: string
}

export function Panel({ title, subtitle, className, children }: PanelProps) {
  return (
    <section
      className={clsx(
        'surface-card section-enter rounded-2xl p-4 md:p-5',
        className,
      )}
    >
      {(title || subtitle) && (
        <header className="mb-4 border-b border-[var(--line)] pb-3">
          {title && (
            <h2 className="font-title text-[18px] font-semibold text-slate-900">{title}</h2>
          )}
          {subtitle && <p className="pt-1 text-sm text-slate-600">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  )
}
