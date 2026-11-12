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
    <article className="mx-auto w-full max-w-3xl px-5 pb-20 pt-32 lg:px-6 lg:pt-36">
      <header className="border-b border-white/[0.08] pb-8">
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Deployment documentation</p>
        <h1 className="mt-4 text-display-sm">{title}</h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted-foreground">{summary}</p>
        <p className="mt-4 text-[11px] text-subtle">Last updated {updated}</p>
      </header>
      <div className="mt-8 space-y-8">{children}</div>
    </article>
  );
}

export function DocSection({ id, title, children }: { id?: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-heading` : undefined} className="space-y-3">
      <h2 id={id ? `${id}-heading` : undefined} className="text-base font-medium tracking-tight text-foreground">
        {title}
      </h2>
      <div className="space-y-2.5 text-sm leading-relaxed text-muted-foreground">{children}</div>
    </section>
  );
}

export function CheckList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item} className="border-l border-white/20 pl-3 text-sm leading-relaxed text-muted-foreground">
          {item}
        </li>
      ))}
    </ul>
  );
}

export function DefinitionList({ items }: { items: { term: string; detail: string }[] }) {
  return (
    <dl className="divide-y divide-border/70">
      {items.map((item) => (
        <div key={item.term} className="py-2.5">
          <dt className="text-sm font-medium text-foreground">{item.term}</dt>
          <dd className="mt-0.5 text-sm leading-relaxed text-muted-foreground">{item.detail}</dd>
        </div>
      ))}
    </dl>
  );
}
