import { Badge } from "@/components/ui/badge";
import { DefinitionList, DocSection, PublicDocument } from "@/components/layout/PublicDocument";

const IMPLEMENTED = [
  {
    term: "Authentication",
    detail:
      "Email and password sign-in issuing signed bearer tokens (JSON Web Tokens). Passwords are hashed with Argon2. Authenticated requests carry the token in the authorization header.",
  },
  {
    term: "Permission-based authorization",
    detail:
      "Every protected route requires a named permission and the API enforces it. The interface hides pages the account cannot use, but the check that matters happens on the server.",
  },
  {
    term: "Tenant scoping",
    detail:
      "Records carry a tenant identifier and reads are filtered by it, including retrieval, structured queries and the graph traversal.",
  },
  {
    term: "Document access levels and access ceiling",
    detail:
      "Documents carry an access level and each account has a ceiling, so a query cannot return a passage above the ceiling even when the query itself is allowed.",
  },
  {
    term: "Rate limiting",
    detail:
      "Configurable fixed-window limits are applied to sign-in, upload and query endpoints, and the limit and window are deployment settings.",
  },
  {
    term: "Audit trail",
    detail:
      "Queries, uploads, document reads, comparisons and evaluation runs are recorded with actor, resource, outcome and request id.",
  },
  {
    term: "Document assets behind authorization",
    detail:
      "Rendered page images are streamed through an authorized route. Storage keys are never handed to the browser, so a guessed URL does not disclose a page.",
  },
  {
    term: "Upload validation",
    detail:
      "File type and size are validated before ingestion, and a checksum identifies duplicate uploads so a document is not indexed twice.",
  },
];

const NOT_IMPLEMENTED = [
  "Single sign-on or SAML, multi-factor authentication, and directory synchronisation.",
  "Encryption of the database or object storage by the application itself. Disk and volume encryption are the operator's responsibility.",
  "Per-document access control lists. Access is governed by the level and ceiling model described above.",
  "Secret management. The signing key has a development default and must be set explicitly for any shared deployment.",
  "Independent security review. No SOC 2, ISO 27001, HIPAA or GDPR compliance is claimed, because none has been obtained.",
  "Automatic account lockout and password policy enforcement beyond the minimum length.",
  "Malware scanning of uploaded files.",
];

export function SecurityPage() {
  return (
    <PublicDocument
      title="Security"
      summary="The controls this build implements, and the ones it does not. Nothing on this page is aspirational: the second list exists so the absence of a control is never mistaken for its presence."
      updated="30 September 2026"
    >
      <DocSection id="implemented" title="Implemented">
        <DefinitionList items={IMPLEMENTED} />
      </DocSection>

      <DocSection id="not-implemented" title="Not implemented">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="border-warning/35 font-normal text-warning">
              planned or absent
            </Badge>
            <span className="text-xs text-muted-foreground">Listed so the gap is explicit.</span>
          </div>
          <ul className="space-y-1.5">
            {NOT_IMPLEMENTED.map((item) => (
              <li key={item} className="border-l pl-3 text-sm leading-relaxed text-muted-foreground">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </DocSection>

      <DocSection id="operator" title="Before running this for real">
        <p>
          Set a unique token signing key, disable self-registration, put the deployment behind TLS and network controls,
          create named accounts with the narrowest role that works, and confirm your retention expectations against the
          retention described on the privacy page. The defaults in this repository are development defaults.
        </p>
      </DocSection>

      <DocSection id="report" title="Reporting an issue">
        <p>
          This is an evaluation build with no security contact or bounty programme. Report anything you find to the
          maintainer of the repository you are running.
        </p>
      </DocSection>
    </PublicDocument>
  );
}
