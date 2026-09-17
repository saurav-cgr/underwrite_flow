// @vitest-environment jsdom
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    code: string;

    // Mirror the real constructor so messages survive into the UI.
    constructor(status: number, message: string, code = "http_error") {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
  createRole: vi.fn(),
  createUser: vi.fn(),
  listPermissions: vi.fn(),
  listRoles: vi.fn(),
  listUsers: vi.fn(),
  updateRole: vi.fn(),
  updateUser: vi.fn(),
}));

import {
  ApiError,
  createRole,
  createUser,
  listPermissions,
  listRoles,
  listUsers,
  updateRole,
  updateUser,
} from "./api";
import { AccessAdministration } from "./access-admin";
import "./test-setup";
import type { PermissionSummary, RoleRecord, UserRecord } from "./types";

const APPLICANT_ROLE: RoleRecord = {
  id: "role-applicant",
  code: "applicant",
  title: "Applicant",
  description: null,
  is_active: true,
  is_system: true,
  permissions: ["cases:read", "cases:write"],
};

const UNDERWRITER_ROLE: RoleRecord = {
  id: "role-underwriter",
  code: "underwriter",
  title: "Underwriter",
  description: null,
  is_active: true,
  is_system: true,
  permissions: ["cases:override", "reviews:read"],
};

const CATALOGUE: PermissionSummary[] = [
  { code: "cases:read", title: "Read cases", description: null },
  { code: "users:manage", title: "Manage users", description: null },
];

const USERS: UserRecord[] = [
  {
    id: "user-underwriter",
    email: "underwriter@synthetic.test",
    display_name: "Synthetic Underwriter",
    is_active: true,
    role: { id: "role-underwriter", code: "underwriter" },
    created_at: "2026-09-17T00:00:00Z",
  },
  {
    id: "user-applicant",
    email: "applicant@synthetic.test",
    display_name: "Synthetic Applicant",
    is_active: false,
    role: { id: "role-applicant", code: "applicant" },
    created_at: "2026-09-17T00:00:00Z",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listUsers).mockResolvedValue(USERS);
  vi.mocked(listRoles).mockResolvedValue([APPLICANT_ROLE, UNDERWRITER_ROLE]);
  vi.mocked(listPermissions).mockResolvedValue(CATALOGUE);
  vi.mocked(updateUser).mockResolvedValue(USERS[0]!);
  vi.mocked(updateRole).mockResolvedValue(APPLICANT_ROLE);
  vi.mocked(createUser).mockResolvedValue(USERS[0]!);
  vi.mocked(createRole).mockResolvedValue(APPLICANT_ROLE);
});

// Render the access panel with one synthetic bearer token.
function renderPanel() {
  return render(<AccessAdministration token="session" />);
}

// Verify the user table captions itself and labels each role control.
describe("access administration users", () => {
  it("renders a captioned table with labelled role controls", async () => {
    renderPanel();

    const table = await screen.findByRole("table", {
      name: /synthetic users, their role, and active state/i,
    });
    expect(
      within(table).getByText("Synthetic Underwriter"),
    ).toBeTruthy();
    expect(
      screen.getByRole("combobox", {
        name: "Role for underwriter@synthetic.test",
      }),
    ).toBeTruthy();
    // Active state is readable as text, not only as a colour.
    expect(within(table).getByText("Active")).toBeTruthy();
    expect(within(table).getByText("Inactive")).toBeTruthy();
  });

  it("saves a role change for one user", async () => {
    const user = userEvent.setup();
    renderPanel();

    const select = await screen.findByRole("combobox", {
      name: "Role for underwriter@synthetic.test",
    });
    await user.selectOptions(select, "role-applicant");

    await waitFor(() =>
      expect(updateUser).toHaveBeenCalledWith("session", "user-underwriter", {
        role_id: "role-applicant",
      }),
    );
  });

  it("deactivates one user without touching the others", async () => {
    const user = userEvent.setup();
    renderPanel();

    const table = await screen.findByRole("table");
    const row = within(table)
      .getByText("Synthetic Underwriter")
      .closest("tr") as HTMLElement;
    await user.click(within(row).getByRole("button", { name: "Deactivate" }));

    await waitFor(() =>
      expect(updateUser).toHaveBeenCalledWith("session", "user-underwriter", {
        is_active: false,
      }),
    );
  });

  it("creates a user from the labelled form", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.type(
      await screen.findByLabelText("Email"),
      "reviewer@synthetic.test",
    );
    await user.type(screen.getByLabelText("Display name"), "Synthetic Reviewer");
    await user.type(
      screen.getByLabelText("Initial password"),
      "synthetic-password",
    );
    await user.click(screen.getByRole("button", { name: "Create user" }));

    await waitFor(() =>
      expect(createUser).toHaveBeenCalledWith("session", {
        email: "reviewer@synthetic.test",
        display_name: "Synthetic Reviewer",
        password: "synthetic-password",
        role_id: "role-applicant",
      }),
    );
  });
});

// Verify role scopes are editable against the live permission catalogue.
describe("access administration roles", () => {
  it("groups each role as a labelled fieldset with its scopes", async () => {
    renderPanel();

    const group = await screen.findByRole("group", {
      name: /Applicant/,
    });
    expect(within(group).getByLabelText("cases:read")).toBeTruthy();
    expect(within(group).getByLabelText("users:manage")).toBeTruthy();
  });

  it("saves the checked scopes back to the role", async () => {
    const user = userEvent.setup();
    renderPanel();

    const group = await screen.findByRole("group", { name: /Applicant/ });
    await user.click(within(group).getByLabelText("users:manage"));
    await user.click(
      within(group).getByRole("button", { name: "Save scopes" }),
    );

    await waitFor(() =>
      expect(updateRole).toHaveBeenCalledWith("session", "role-applicant", {
        permissions: ["cases:read", "cases:write", "users:manage"],
      }),
    );
  });

  it("creates a role from the selected scopes", async () => {
    const user = userEvent.setup();
    renderPanel();

    const form = (
      await screen.findByRole("button", { name: "Create role" })
    ).closest("form") as HTMLElement;
    await user.type(within(form).getByLabelText(/^Code/), "claims_reviewer");
    await user.type(
      within(form).getByLabelText("Title"),
      "Claims Reviewer",
    );
    await user.click(within(form).getByLabelText("cases:read"));
    await user.click(screen.getByRole("button", { name: "Create role" }));

    await waitFor(() =>
      expect(createRole).toHaveBeenCalledWith("session", {
        code: "claims_reviewer",
        title: "Claims Reviewer",
        description: undefined,
        permissions: ["cases:read"],
      }),
    );
  });
});

// Verify a refused request is announced as an alert rather than swallowed.
describe("access administration failures", () => {
  it("announces a load failure in an alert region", async () => {
    vi.mocked(listUsers).mockRejectedValue(
      new ApiError(403, "Forbidden", "forbidden"),
    );
    renderPanel();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Forbidden");
  });

  it("announces a refused change and keeps the panel usable", async () => {
    const user = userEvent.setup();
    vi.mocked(createUser).mockRejectedValue(
      new ApiError(409, "User already exists", "user_exists"),
    );
    renderPanel();

    await user.type(
      await screen.findByLabelText("Email"),
      "reviewer@synthetic.test",
    );
    await user.type(screen.getByLabelText("Display name"), "Synthetic Reviewer");
    await user.type(
      screen.getByLabelText("Initial password"),
      "synthetic-password",
    );
    await user.click(screen.getByRole("button", { name: "Create user" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("User already exists");
    const submit = screen.getByRole("button", {
      name: "Create user",
    }) as HTMLButtonElement;
    expect(submit.disabled).toBe(false);
  });
});
