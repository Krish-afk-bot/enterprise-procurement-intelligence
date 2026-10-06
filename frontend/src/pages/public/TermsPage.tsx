import { CheckList, DocSection, PublicDocument } from "@/components/layout/PublicDocument";

export function TermsPage() {
  return (
    <PublicDocument
      title="Terms"
      summary="The conditions for using this build. It is an evaluation and demonstration deployment, not a commercial service with a service level agreement."
      updated="30 September 2026"
    >
      <DocSection id="what-this-is" title="What this build is">
        <p>
          Procurement Intelligence is a self-hosted application for searching procurement documents and the records
          extracted from them. It is provided for evaluation, development and coursework. It is not offered as a hosted
          product and no certification, accreditation or uptime commitment is claimed for it.
        </p>
      </DocSection>

      <DocSection id="use" title="Acceptable use">
        <CheckList
          items={[
            "Only upload documents you are authorised to process. Access levels and the account ceiling restrict who can read them afterwards, but they do not give you permission to hold the content.",
            "Do not attempt to bypass authentication, permission checks, document access levels or rate limits.",
            "Do not use the deployment to process unlawful material.",
            "Treat answers as evidence pointers, not as legal advice. Verify anything material against the cited page before acting on it.",
          ]}
        />
      </DocSection>

      <DocSection id="accounts" title="Accounts">
        <p>
          Accounts are created by an administrator or, where self-registration is enabled, by the user. An operator may
          disable self-registration, change a role, or remove an account. Permissions map to API permissions and are
          enforced by the API itself, not only by the interface.
        </p>
      </DocSection>

      <DocSection id="availability" title="Availability and warranty">
        <p>
          The software is provided as is, without warranties of any kind, including fitness for a particular purpose.
          There is no service level agreement. Features may change or be removed, and stored data may be reset by the
          operator of an instance.
        </p>
      </DocSection>

      <DocSection id="answers" title="Answers and accuracy">
        <p>
          Answers are generated from retrieved passages and verified against them. That reduces unsupported statements,
          it does not eliminate error. Every answer states its verification outcome, and the system refuses when it
          cannot find supporting evidence. A refusal means the corpus did not support the question; it does not mean the
          answer does not exist somewhere else.
        </p>
      </DocSection>

      <DocSection id="liability" title="Liability">
        <p>
          To the extent permitted by applicable law, the maintainers of this build are not liable for decisions taken on
          the basis of its output, or for any data loss resulting from operating it.
        </p>
      </DocSection>

      <DocSection id="changes" title="Changes">
        <p>
          These terms describe the current build and may be updated with it. The date at the top of the page shows when
          they last changed.
        </p>
      </DocSection>
    </PublicDocument>
  );
}
