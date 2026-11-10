import type { ReactNode } from "react";

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl tracking-tight text-forest">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Badge({ className, children }: { className: string; children: ReactNode }) {
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${className}`}>{children}</span>;
}

export function Notice({ children }: { children: ReactNode }) {
  return <div className="mb-4 rounded-xl border border-pale bg-white px-4 py-3 text-sm leading-6 text-deep">{children}</div>;
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-pale bg-white px-6 py-10 text-center">
      <h2 className="font-display text-xl">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{body}</p>
    </div>
  );
}
