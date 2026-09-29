// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api-knowledge", () => ({
  acceptRegulationTags: vi.fn(),
}));

import { acceptRegulationTags } from "./api-knowledge";
import { KnowledgeTags } from "./knowledge-tags";
import "./test-setup";

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(acceptRegulationTags).mockResolvedValue({
    passage_key: "circular#2",
    topic_tags: ["claim-settlement"],
    limits: [],
  });
});

// Verify an administrator accepts a suggested tag on one draft clause.
describe("regulation tag review", () => {
  it("accepts a suggested tag and shows it as accepted", async () => {
    const user = userEvent.setup();
    render(
      <KnowledgeTags
        editable
        passageKey="circular#2"
        suggestedTags={["claim-settlement", "renewal"]}
        token="session"
        topicTags={[]}
        versionId="version-1"
      />,
    );

    expect(screen.getByText(/Suggested tags/)).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Accept claim-settlement" }),
    );

    expect(acceptRegulationTags).toHaveBeenCalledWith(
      "session",
      "version-1",
      "circular#2",
      ["claim-settlement"],
    );
    expect(await screen.findByText(/Accepted: claim-settlement/))
      .toBeTruthy();
  });

  it("offers no tag control outside a draft", () => {
    const { container } = render(
      <KnowledgeTags
        editable={false}
        passageKey="circular#2"
        suggestedTags={["claim-settlement"]}
        token="session"
        topicTags={[]}
        versionId="version-1"
      />,
    );

    expect(container.textContent).toBe("");
  });
});
