import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CitationChip } from "../Evidence";
import type { Citation } from "@/lib/types";

const citation: Citation = {
  chunk_id: "chk_1",
  document_id: "doc_1",
  document_name: "supplier_a_master_contract.pdf",
  document_type: "contract",
  page: 4,
  section: "Price Schedule",
  clause: "4.2",
  snippet: "The unit price for Industrial Laptop X200 is USD 920.00",
  source_uri: null,
  score: 0.8,
  rank: 1,
  evidence_type: "document",
  is_synthetic: true,
  verified: true,
  label: "supplier_a_master_contract.pdf — p.4",
};

describe("CitationChip", () => {
  it("shows the source document and page and links to the viewer", () => {
    render(
      <MemoryRouter>
        <CitationChip citation={citation} index={1} />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link", { name: /supplier_a_master_contract\.pdf/i });
    expect(link).toHaveAttribute("href", "/documents/doc_1?page=4&chunk=chk_1");
    expect(screen.getByText("p.4")).toBeInTheDocument();
  });
});
