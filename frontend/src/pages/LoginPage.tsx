import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, BadgeCheck, FileSearch, ShieldQuestion } from "lucide-react";

import { Logo } from "@/components/brand/Logo";
import { StaticWaveField } from "@/components/three/hero/LazyWaveHero";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { type CredentialErrors, hasErrors, validateCredentials } from "@/lib/validation";
import { useAuth } from "@/store/auth";

const PRINCIPLES = [
  {
    icon: FileSearch,
    title: "Evidence first",
    body: "Answers arrive with the document and page they came from, and the viewer opens on that page.",
  },
  {
    icon: BadgeCheck,
    title: "Verification stated",
    body: "Each answer reports whether its statements were supported, partial, conflicting or unsupported.",
  },
  {
    icon: ShieldQuestion,
    title: "Refusals kept honest",
    body: "When the corpus does not support a question, the system says so instead of inventing a value.",
  },
];

export function LoginPage() {
  const { login, register, token, error, status } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [busy, setBusy] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<CredentialErrors>({});

  if (token) return <Navigate to="/ask" replace />;

  const isSignIn = mode === "signin";

  function clearFieldError(field: keyof CredentialErrors) {
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    // Validate before the request: a malformed address or a too-short new
    // password would otherwise come back as a generic API error.
    const errors = validateCredentials({ mode, email, password, fullName });
    setFieldErrors(errors);
    if (hasErrors(errors)) return;
    setBusy(true);
    try {
      if (isSignIn) {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
      navigate("/ask", { replace: true });
    } catch {
      // The store surfaces the message below the form.
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative grid min-h-screen overflow-x-clip bg-ink lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
      {/* ------------------------------------------------------------ narrative */}
      <aside className="relative hidden overflow-hidden border-r border-white/[0.07] lg:flex lg:flex-col lg:justify-between lg:px-14 lg:py-12">
        <div className="pointer-events-none absolute inset-0 opacity-70" aria-hidden="true">
          <StaticWaveField />
        </div>
        <div
          className="pointer-events-none absolute left-1/3 top-1/3 h-[520px] w-[620px] -translate-x-1/2 -translate-y-1/2 halo"
          aria-hidden="true"
        />
        <div className="pointer-events-none absolute inset-0 grid-lines opacity-40" aria-hidden="true" />

        <Link to="/" className="relative w-fit">
          <Logo />
          <span className="sr-only">— back to product overview</span>
        </Link>

        <div className="relative max-w-lg">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-subtle">The workspace</p>
          <h2 className="mt-4 text-display-sm">
            A procurement workspace built around evidence, not around a chat window.
          </h2>
          <ul className="mt-9 space-y-6">
            {PRINCIPLES.map((principle) => (
              <li key={principle.title} className="flex gap-3.5">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/12 bg-white/[0.05]">
                  <principle.icon className="h-4 w-4 text-white/80" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-[13.5px] font-medium">{principle.title}</p>
                  <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">{principle.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative max-w-md text-[11px] leading-relaxed text-subtle">
          Access is enforced by the API. Every answer is filtered by tenant and by the document access level of the
          signed-in account.
        </p>
      </aside>

      {/* ----------------------------------------------------------------- form */}
      <div className="relative flex items-center justify-center px-5 py-12 sm:px-8">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[560px] -translate-x-1/2 halo opacity-60 lg:hidden"
          aria-hidden="true"
        />
        <div className="relative w-full max-w-[380px]">
          <Link to="/" className="mb-10 inline-block lg:hidden">
            <Logo />
            <span className="sr-only">— back to product overview</span>
          </Link>

          <div className="glass-strong rounded-2xl p-7 shadow-card sm:p-8">
            <h1 className="text-2xl font-semibold tracking-tight">{isSignIn ? "Sign in" : "Create an account"}</h1>
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
              {isSignIn
                ? "Use the account issued by the operator of this deployment."
                : "Self-registration must be enabled on the deployment for this to succeed."}
            </p>

            <div
              role="tablist"
              aria-label="Authentication mode"
              className="mt-6 grid grid-cols-2 gap-1 rounded-full border border-white/10 bg-white/[0.03] p-1"
            >
              {(["signin", "register"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={mode === value}
                  onClick={() => setMode(value)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-[12px] font-medium transition-colors duration-control",
                    mode === value
                      ? "bg-white text-ink"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {value === "signin" ? "Sign in" : "Register"}
                </button>
              ))}
            </div>

            <form onSubmit={submit} className="mt-6 space-y-5">
              {!isSignIn ? (
                <div className="space-y-2">
                  <Label htmlFor="full-name">Full name</Label>
                  <Input
                    id="full-name"
                    value={fullName}
                    autoComplete="name"
                    required
                    aria-invalid={Boolean(fieldErrors.fullName)}
                    aria-describedby={fieldErrors.fullName ? "full-name-error" : undefined}
                    onChange={(event) => {
                      setFullName(event.target.value);
                      clearFieldError("fullName");
                    }}
                    placeholder="Jamie Chen"
                  />
                  {fieldErrors.fullName ? (
                    <p id="full-name-error" className="text-[11px] text-destructive">
                      {fieldErrors.fullName}
                    </p>
                  ) : null}
                </div>
              ) : null}

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  autoComplete="email"
                  required
                  spellCheck={false}
                  aria-invalid={Boolean(fieldErrors.email)}
                  aria-describedby={fieldErrors.email ? "email-error" : undefined}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    clearFieldError("email");
                  }}
                  placeholder="name@company.com"
                />
                {fieldErrors.email ? (
                  <p id="email-error" className="text-[11px] text-destructive">
                    {fieldErrors.email}
                  </p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  autoComplete={isSignIn ? "current-password" : "new-password"}
                  required
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={fieldErrors.password ? "password-error" : undefined}
                  onChange={(event) => {
                    setPassword(event.target.value);
                    clearFieldError("password");
                  }}
                />
                {fieldErrors.password ? (
                  <p id="password-error" className="text-[11px] text-destructive">
                    {fieldErrors.password}
                  </p>
                ) : null}
              </div>

              {error && status === "error" ? (
                <p
                  role="alert"
                  className="flex items-start gap-2 rounded-lg border border-destructive/35 bg-destructive/10 p-3 text-xs text-destructive"
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {error}
                </p>
              ) : null}

              <Button type="submit" variant="glow" className="w-full" disabled={busy}>
                {busy ? (isSignIn ? "Signing in" : "Creating account") : isSignIn ? "Sign in" : "Create account"}
                {busy ? null : <ArrowRight className="h-4 w-4" aria-hidden="true" />}
              </Button>
            </form>
          </div>

          <p className="mt-6 px-1 text-[11px] leading-relaxed text-subtle">
            By signing in you accept the{" "}
            <Link to="/terms" className="text-muted-foreground underline decoration-white/25 underline-offset-2 hover:text-foreground">
              terms
            </Link>{" "}
            and the{" "}
            <Link to="/privacy" className="text-muted-foreground underline decoration-white/25 underline-offset-2 hover:text-foreground">
              privacy
            </Link>{" "}
            description for this deployment. Security controls and their limits are documented on the{" "}
            <Link to="/security" className="text-muted-foreground underline decoration-white/25 underline-offset-2 hover:text-foreground">
              security
            </Link>{" "}
            page.
          </p>

          <p className="mt-4 px-1 text-[11px] text-subtle">
            <Link to="/" className="transition-colors hover:text-foreground">
              Back to product overview
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
