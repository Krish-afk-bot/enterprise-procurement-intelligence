import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { AlertTriangle, BadgeCheck, FileSearch, ShieldQuestion } from "lucide-react";

import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { cn } from "@/lib/utils";
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

  if (token) return <Navigate to="/ask" replace />;

  const isSignIn = mode === "signin";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
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
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
      <aside className="hidden flex-col justify-between border-r bg-muted/30 px-10 py-12 lg:flex">
        <Link to="/" className="w-fit" aria-label="Back to product overview">
          <Logo />
        </Link>
        <div className="max-w-md">
          <h2 className="text-xl font-semibold leading-snug tracking-tight">
            A procurement workspace built around evidence, not around a chat window.
          </h2>
          <ul className="mt-7 space-y-5">
            {PRINCIPLES.map((principle) => (
              <li key={principle.title} className="flex gap-3">
                <principle.icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                <div>
                  <p className="text-sm font-medium">{principle.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{principle.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="max-w-md text-xs leading-relaxed text-muted-foreground">
          Access is enforced by the API. Every answer is filtered by tenant and by the document access level of the
          signed-in account.
        </p>
      </aside>

      <div className="flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm">
          <Link to="/" className="mb-8 inline-block lg:hidden" aria-label="Back to product overview">
            <Logo />
          </Link>

          <h1 className="text-xl font-semibold tracking-tight">{isSignIn ? "Sign in" : "Create an account"}</h1>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {isSignIn
              ? "Use the account issued by the operator of this deployment."
              : "Self-registration must be enabled on the deployment for this to succeed."}
          </p>

          <div role="tablist" aria-label="Authentication mode" className="mt-6 grid grid-cols-2 gap-1 rounded-md border p-1">
            {(["signin", "register"] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={mode === value}
                onClick={() => setMode(value)}
                className={cn(
                  "rounded px-3 py-1.5 text-xs font-medium transition-colors duration-micro",
                  mode === value ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {value === "signin" ? "Sign in" : "Register"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="mt-5 space-y-4">
            {!isSignIn ? (
              <div className="space-y-1.5">
                <Label htmlFor="full-name">Full name</Label>
                <Input
                  id="full-name"
                  value={fullName}
                  autoComplete="name"
                  required
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Jamie Chen"
                />
              </div>
            ) : null}

            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                autoComplete="email"
                required
                spellCheck={false}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@company.com"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                autoComplete={isSignIn ? "current-password" : "new-password"}
                required
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>

            {error && status === "error" ? (
              <p role="alert" className="flex items-start gap-2 rounded-md border border-destructive/35 bg-destructive/5 p-2.5 text-xs">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" aria-hidden="true" />
                {error}
              </p>
            ) : null}

            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? (isSignIn ? "Signing in" : "Creating account") : isSignIn ? "Sign in" : "Create account"}
            </Button>
          </form>

          <p className="mt-6 text-[11px] leading-relaxed text-muted-foreground">
            By signing in you accept the{" "}
            <Link to="/terms" className="underline hover:text-foreground">
              terms
            </Link>{" "}
            and the{" "}
            <Link to="/privacy" className="underline hover:text-foreground">
              privacy
            </Link>{" "}
            description for this deployment. Security controls and their limits are documented on the{" "}
            <Link to="/security" className="underline hover:text-foreground">
              security
            </Link>{" "}
            page.
          </p>
        </div>
      </div>
    </div>
  );
}
