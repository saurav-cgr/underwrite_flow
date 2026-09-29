// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api-knowledge", () => ({
  askQuestion: vi.fn(),
  listQuestions: vi.fn(),
}));

import { askQuestion, listQuestions } from "./api-knowledge";
import { GuidanceQuestions } from "./guidance-questions";
import type { CaseQuestion } from "./types-knowledge";
import "./test-setup";

const EARLIER: CaseQuestion = {
  id: "q-1",
  question: "Does high cover need an income record?",
  answer: "The pinned guidance on High requested cover applies.",
  covered: true,
  citations: [{ version: "g1", passage_key: "life-cover-high-sum-assured" }],
  asked_by: "Synthetic Underwriter",
  created_at: "2026-09-28T10:00:00Z",
};

const FALLBACK: CaseQuestion = {
  id: "q-2",
  question: "Zebra xylophone quokka?",
  answer: "not covered by guidelines",
  covered: false,
  citations: [],
  asked_by: "Second Synthetic Underwriter",
  created_at: "2026-09-28T10:05:00Z",
};

// Start each test with one stored question in the shared history.
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listQuestions).mockResolvedValue([EARLIER]);
  vi.mocked(askQuestion).mockResolvedValue(FALLBACK);
});

describe("guidance questions", () => {
  // Verify the question field has an accessible label.
  it("renders a labelled question input", async () => {
    render(<GuidanceQuestions token="session" caseId="case-id" />);

    expect(
      await screen.findByLabelText("Ask about this case"),
    ).toBeTruthy();
  });

  // Verify pressing Enter submits the typed question.
  it("submits with the keyboard", async () => {
    const user = userEvent.setup();
    render(<GuidanceQuestions token="session" caseId="case-id" />);

    await user.type(
      await screen.findByLabelText("Ask about this case"),
      "Zebra xylophone quokka?{Enter}",
    );

    expect(askQuestion).toHaveBeenCalledWith(
      "session",
      "case-id",
      "Zebra xylophone quokka?",
    );
    expect(await screen.findByText(FALLBACK.question)).toBeTruthy();
  });

  // Verify a pending answer shows a busy status and disables submit.
  it("announces a busy status while answering", async () => {
    const user = userEvent.setup();
    vi.mocked(askQuestion).mockReturnValue(new Promise(() => undefined));
    render(<GuidanceQuestions token="session" caseId="case-id" />);

    await user.type(
      await screen.findByLabelText("Ask about this case"),
      "Covered?{Enter}",
    );

    expect(
      screen.getByRole("status", { name: "Answering question" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Ask" }).hasAttribute("disabled"),
    ).toBe(true);
  });

  // Verify the fallback answer carries a visible text cue.
  it("shows the fallback with a text cue", async () => {
    vi.mocked(listQuestions).mockResolvedValue([FALLBACK]);
    render(<GuidanceQuestions token="session" caseId="case-id" />);

    expect(await screen.findByText("Not covered")).toBeTruthy();
    expect(screen.getByText("not covered by guidelines")).toBeTruthy();
  });

  // Verify shared history lists askers, answers, and citations in order.
  it("renders the shared history list", async () => {
    vi.mocked(listQuestions).mockResolvedValue([EARLIER, FALLBACK]);
    render(<GuidanceQuestions token="session" caseId="case-id" />);

    const history = await screen.findByRole("list", {
      name: "Question history",
    });
    const items = history.querySelectorAll(":scope > li");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain(EARLIER.question);
    expect(items[0].textContent).toContain("life-cover-high-sum-assured");
    expect(items[1].textContent).toContain("Second Synthetic Underwriter");
  });
});
