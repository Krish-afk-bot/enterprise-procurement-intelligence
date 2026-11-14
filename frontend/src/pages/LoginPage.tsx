import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, BadgeCheck, Eye, EyeOff, FileSearch, ShieldQuestion } from "lucide-react";

import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { type CredentialErrors, hasErrors, validateCredentials } from "@/lib/validation";
import { useAuth } from "@/store/auth";
import { useMotionMode } from "@/motion/motion";

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
  const motionMode = useMotionMode();
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
      <aside className="relative hidden overflow-hidden border-r border-white/[0.08] bg-[#070708] lg:flex lg:flex-col lg:justify-between lg:px-14 lg:py-12">
        {/* Lightweight ambient visual: Slow orange beam drift + circuit pulses (SVG/CSS, obeys Motion mode) */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div
            className={cn(
              "absolute -top-32 -left-32 w-[500px] h-[500px] bg-gradient-to-br from-[#FF4D00]/25 via-[#FF7A1A]/8 to-transparent rounded-full blur-[120px] transition-transform duration-1000",
              motionMode === "full" ? "animate-pulse duration-[7000ms]" : ""
            )}
          />
          <svg className="absolute inset-0 w-full h-full opacity-25" xmlns="http://www.w3.org/2000/svg">
            <line x1="25%" y1="0%" x2="25%" y2="100%" stroke="rgba(255,77,0,0.2)" strokeWidth="1" strokeDasharray="6 8" />
            <line x1="75%" y1="0%" x2="75%" y2="100%" stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="4 6" />
            <line x1="0%" y1="40%" x2="100%" y2="40%" stroke="rgba(255,77,0,0.12)" strokeWidth="1" />
            <circle cx="25%" cy="40%" r="4" fill="#FF4D00" className={cn(motionMode === "full" ? "animate-ping" : "")} />
            <circle cx="25%" cy="40%" r="2" fill="#FFFFFF" />
            <circle cx="75%" cy="70%" r="3" fill="#FF7A1A" />
          </svg>
        </div>
        
        <div className="relative z-10 flex items-center justify-between">
          <Link to="/" className="group flex items-center gap-2.5" aria-label="EPI home">
            <Logo variant="lockup" size={32} />
          </Link>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono uppercase tracking-wider bg-white/5 border border-white/10 text-white/70">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF4D00]" />
            Enterprise Edition
          </span>
        </div>

        <div className="relative z-10 my-auto py-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-mono tracking-wider uppercase bg-[#FF4D00]/10 text-[#FF7A1A] border border-[#FF4D00]/20 mb-6">
            EVIDENCE-GROUNDED REASONING
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white mb-4 leading-tight">
            A procurement workspace built around evidence, not around a chat window.
          </h2>
          <p className="text-sm text-white/60 leading-relaxed max-w-md mb-8">
            Access contracts, tenders, rate cards, and supplier networks with strict tenant isolation and verifiable source citations.
          </p>

          <div className="flex flex-col gap-4">
            {PRINCIPLES.map((principle) => {
              const Icon = principle.icon;
              return (
                <div
                  key={principle.title}
                  className="flex items-start gap-3.5 p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-md"
                >
                  <div className="w-8 h-8 rounded-xl bg-white/5 flex items-center justify-center text-[#FF4D00] shrink-0 mt-0.5">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-white tracking-wide">{principle.title}</h3>
                    <p className="text-[11px] text-white/50 leading-relaxed mt-0.5">{principle.body}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="relative z-10 pt-6 border-t border-white/[0.08] flex items-center justify-between text-xs text-white/40">
          <span>Enterprise Tenant Isolation</span>
          <span>Argon2id + JWT Bearer</span>
        </div>
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

          <div className="rounded-3xl bg-[#0B0B0C] border border-white/10 p-7 shadow-2xl sm:p-8 backdrop-blur-xl">
            <h1 className="text-2xl font-bold tracking-tight text-white">{isSignIn ? "Sign in" : "Create an account"}</h1>
            <p className="mt-1.5 text-xs leading-relaxed text-white/60">
              {isSignIn
                ? "Use the account issued by the operator of this deployment."
                : "Self-registration must be enabled on the deployment for this to succeed."}
            </p>

            <div
              role="tablist"
              aria-label="Authentication mode"
              className="mt-6 grid grid-cols-2 gap-1 rounded-full border border-white/10 bg-white/[0.04] p-1"
            >
              {(["signin", "register"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={mode === value}
                  onClick={() => setMode(value)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200",
                    mode === value
                      ? "bg-[#FF4D00] text-white shadow-md shadow-[#FF4D00]/30"
                      : "text-white/60 hover:text-white",
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
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    autoComplete={isSignIn ? "current-password" : "new-password"}
                    required
                    aria-invalid={Boolean(fieldErrors.password)}
                    aria-describedby={fieldErrors.password ? "password-error" : undefined}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      clearFieldError("password");
                    }}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white transition-colors p-1 rounded focus:outline-none focus-visible:ring-1 focus-visible:ring-[#FF4D00]"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
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

              <Button type="submit" className="w-full bg-[#FF4D00] hover:bg-[#FF7A1A] text-white font-semibold rounded-xl py-3 shadow-lg shadow-[#FF4D00]/25 transition-all duration-200" disabled={busy}>
                {busy ? (isSignIn ? "Signing in..." : "Creating account...") : isSignIn ? "Sign in to workspace" : "Create account"}
                {busy ? null : <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />}
              </Button>
            </form>
          </div>

          <div className="mt-8 pt-4 border-t border-white/5 flex items-center justify-between text-[11px] text-white/40 font-mono">
            <span>Argon2id + JWT Bearer</span>
            <span>Tenant Isolation Enforced</span>
          </div>

          <p className="mt-4 px-1 text-[11px] leading-relaxed text-subtle">
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
