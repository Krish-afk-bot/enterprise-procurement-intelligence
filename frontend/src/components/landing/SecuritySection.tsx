import { Link } from "react-router-dom";
import { ArrowRight, FileKey, Fingerprint, ShieldCheck, Users } from "lucide-react";

import { Reveal } from "@/components/motion/Reveal";

/**
 * Security and trust, limited to what this build actually enforces.
 *
 * No certification, encryption guarantee or compliance standard is claimed —
 * the security page lists the controls the deployment does not implement, and
 * this section links to it rather than summarising past it.
 */
const CONTROLS = [
  {
    icon: Users,
    title: "Every read is tenant-scoped",
    body: "Procurement records, retrieval and graph traversal are filtered by the tenant on the record, not by a client-supplied identifier.",
  },
  {
    icon: Fingerprint,
    title: "Sessions, not secrets in storage",
    body: "Sign-in issues short-lived bearer tokens with a silent refresh; the access token is held in memory rather than written to browser storage.",
  },
  {
    icon: FileKey,
    title: "Access levels and a ceiling",
    body: "Documents carry an access level and each account has a ceiling, so an allowed query still cannot return a passage above it.",
  },
  {
    icon: ShieldCheck,
    title: "Traceable by default",
    body: "Queries, uploads, document reads, comparisons and evaluation runs are recorded with actor, resource, outcome and request id.",
  },
];

export function SecuritySection() {
  return (
    <section
      id="security"
      className="relative scroll-mt-24 overflow-hidden border-t border-white/[0.07] bg-ink-2 px-5 py-24 lg:px-8 lg:py-28"
    >
      <div className="relative mx-auto w-full max-w-7xl">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-16">
          <Reveal>
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">Security and trust</p>
            <h2 className="mt-4 text-display-sm text-balance">Scoped by tenant. Checked by permission.</h2>
            <p className="mt-4 max-w-md text-[14px] leading-relaxed text-muted-foreground">
              The interface hides what an account cannot use, but the check that matters happens on the server. This
              build claims no certification, because none has been obtained.
            </p>
            <Link
              to="/security"
              className="mt-6 inline-flex items-center gap-1.5 text-[13px] text-foreground underline decoration-white/25 underline-offset-4 transition-colors hover:decoration-white"
            >
              Read the full security model
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </Reveal>

          <div className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/[0.06] sm:grid-cols-2">
            {CONTROLS.map((control, index) => (
              <Reveal key={control.title} delay={index * 70}>
                <div className="h-full bg-ink-2 p-5">
                  <control.icon className="h-4 w-4 text-white/60" aria-hidden="true" />
                  <h3 className="mt-4 text-[13.5px] font-medium tracking-tight">{control.title}</h3>
                  <p className="mt-2 text-[12px] leading-relaxed text-muted-foreground">{control.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>

        <Reveal delay={100}>
          <p className="mt-8 border-t border-white/[0.08] pt-5 text-[11px] leading-relaxed text-subtle">
            Not implemented, and therefore not claimed: single sign-on, multi-factor authentication, per-document
            access lists, application-level encryption at rest, malware scanning, and any independent security review.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
