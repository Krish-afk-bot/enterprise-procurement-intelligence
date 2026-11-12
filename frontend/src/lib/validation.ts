/** Client-side validation for the sign-in / registration form.
 *
 * The API remains the authority: these checks only stop an obviously invalid
 * submission and put the message next to the field that caused it. Rules are
 * deliberately identical for both modes wherever the API is the same, and are
 * stricter for registration (a new password must be long enough to be usable).
 */

export type AuthMode = "signin" | "register";

export interface CredentialInput {
  mode: AuthMode;
  email: string;
  password: string;
  fullName?: string;
}

export type CredentialErrors = Partial<Record<"email" | "password" | "fullName", string>>;

/** Pragmatic address check: one @, a dot in the domain, no spaces. */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export const MIN_PASSWORD_LENGTH = 8;

export function validateCredentials(input: CredentialInput): CredentialErrors {
  const errors: CredentialErrors = {};
  const email = input.email.trim();
  const password = input.password;

  if (!email) {
    errors.email = "Enter the email address for your account.";
  } else if (!EMAIL_RE.test(email)) {
    errors.email = "Enter an email address in the form name@company.com.";
  }

  if (!password) {
    errors.password = "Enter your password.";
  } else if (input.mode === "register" && password.length < MIN_PASSWORD_LENGTH) {
    errors.password = `Use at least ${MIN_PASSWORD_LENGTH} characters for a new password.`;
  }

  if (input.mode === "register") {
    const name = (input.fullName ?? "").trim();
    if (name.length < 2) {
      errors.fullName = "Enter the name the account should display.";
    }
  }

  return errors;
}

export function hasErrors(errors: CredentialErrors): boolean {
  return Object.keys(errors).length > 0;
}
