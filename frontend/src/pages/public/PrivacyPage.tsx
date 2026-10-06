import { CheckList, DefinitionList, DocSection, PublicDocument } from "@/components/layout/PublicDocument";

export function PrivacyPage() {
  return (
    <PublicDocument
      title="Privacy"
      summary="What this deployment stores when you use it, where it is stored, and what does not happen to it. This describes the software in this repository, not a hosted commercial service."
      updated="30 September 2026"
    >
      <DocSection id="scope" title="Scope">
        <p>
          This is a self-hosted procurement intelligence application. The operator of an instance decides where it runs
          and who may use it. The text below describes the data the application itself writes and reads.
        </p>
      </DocSection>

      <DocSection id="stored" title="What is stored">
        <DefinitionList
          items={[
            {
              term: "Account records",
              detail:
                "Email address, display name, role, tenant and a password hash. Passwords are hashed with Argon2 and are never stored or logged in plain text.",
            },
            {
              term: "Documents you upload",
              detail:
                "The original file bytes, plus everything derived from them: pages, extracted or OCR text, layout blocks, tables, chunks, and embeddings.",
            },
            {
              term: "Procurement records extracted from documents",
              detail:
                "Suppliers, contracts, amendments, products, price rows, compliance certificates and the page each row came from.",
            },
            {
              term: "Questions and answers",
              detail:
                "The query text, the answer, its status, the citations that survived verification, the retrieval steps and timing figures.",
            },
            {
              term: "Agent traces and audit entries",
              detail:
                "Which pipeline node ran and what it returned, plus an audit record per query, upload, comparison, evaluation and document read, with actor, resource and request id.",
            },
            {
              term: "Evaluation data",
              detail: "Evaluation runs, per-question results and the metrics computed from them.",
            },
          ]}
        />
      </DocSection>

      <DocSection id="where" title="Where it is stored">
        <p>
          In the workspace database (SQLite by default, PostgreSQL when configured), in the configured vector index,
          graph index and cache, and on the storage backend for uploaded files. All of these run on the operator&apos;s
          own infrastructure in a default deployment.
        </p>
      </DocSection>

      <DocSection id="not-done" title="What this build does not do">
        <CheckList
          items={[
            "No analytics, advertising or tracking scripts are bundled with the frontend.",
            "No data is sold, shared or aggregated across tenants.",
            "No document text leaves the deployment in the default configuration, because no external model endpoint is configured.",
            "If an operator configures a language or vision model endpoint, the prompt sent to that endpoint contains the retrieved passages needed to answer, and that provider's own terms apply.",
          ]}
        />
      </DocSection>

      <DocSection id="retention" title="Retention">
        <p>
          Nothing expires automatically. Deleting a document removes it together with the pages, chunks, tables, prices
          and graph entries derived from it. Audit entries and traces remain until an operator removes them from the
          database.
        </p>
      </DocSection>

      <DocSection id="controls" title="Your controls">
        <CheckList
          items={[
            "Delete an uploaded document and everything derived from it from the document viewer.",
            "Sign out, which discards the access token held by the browser.",
            "Document access levels and the account access ceiling decide which records a signed-in account can read or query.",
            "There is no self-service account deletion endpoint in this build. Ask the operator to remove the account record.",
          ]}
        />
      </DocSection>

      <DocSection id="demo" title="Demo corpus">
        <p>
          The corpus bundled with this build is a labelled synthetic dataset used for demonstration and evaluation.
          Treat a shared instance as a demo environment and do not upload confidential documents to it.
        </p>
      </DocSection>

      <DocSection id="contact" title="Contact">
        <p>
          This project has no legal entity, no data protection officer and no formal compliance certification. The
          maintainer of the repository you are running is the contact point for data questions.
        </p>
      </DocSection>
    </PublicDocument>
  );
}
