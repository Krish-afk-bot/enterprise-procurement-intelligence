export function PublicDocument({
  title,
  summary,
  updated,
  children,
}: {
  title: string;
  summary: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <article className="mx-auto w-full max-w-4xl px-6 pb-24 pt-32 lg:pt-36">
      <header className="relative rounded-3xl bg-[#0B0B0C] border border-white/10 p-8 sm:p-12 mb-12 shadow-2xl overflow-hidden">
        {/* Soft orange atmospheric beam glow */}
        <div className="pointer-events-none absolute -top-24 -right-24 w-80 h-80 bg-gradient-to-br from-[#FF4D00]/20 via-[#FF7A1A]/5 to-transparent rounded-full blur-3xl" />

        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-mono uppercase tracking-wider bg-white/5 border border-white/10 text-[#FF7A1A] mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF4D00]" />
            Deployment Governance
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-white mb-4">{title}</h1>
          <p className="text-sm sm:text-base text-white/70 max-w-2xl leading-relaxed mb-6">{summary}</p>
          <div className="text-xs font-mono text-white/40 pt-4 border-t border-white/10">
            Last updated: {updated}
          </div>
        </div>
      </header>
      <div className="space-y-10">{children}</div>
    </article>
  );
}

export function DocSection({ id, title, children }: { id?: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-heading` : undefined} className="rounded-3xl bg-[#0B0B0C] border border-white/10 p-7 sm:p-9 shadow-lg">
      <h2 id={id ? `${id}-heading` : undefined} className="text-xl font-bold tracking-tight text-white mb-4 flex items-center gap-3">
        <span className="w-2 h-2 rounded-full bg-[#FF4D00]" />
        {title}
      </h2>
      <div className="text-sm leading-relaxed text-white/70 space-y-4">{children}</div>
    </section>
  );
}

export function CheckList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item} className="border-l-2 border-[#FF4D00]/60 pl-3.5 text-sm leading-relaxed text-white/80">
          {item}
        </li>
      ))}
    </ul>
  );
}

export function DefinitionList({ items }: { items: { term: string; detail: string }[] }) {
  return (
    <dl className="divide-y divide-white/10">
      {items.map((item) => (
        <div key={item.term} className="py-3.5">
          <dt className="text-sm font-semibold text-white tracking-wide">{item.term}</dt>
          <dd className="mt-1 text-sm leading-relaxed text-white/60">{item.detail}</dd>
        </div>
      ))}
    </dl>
  );
}
