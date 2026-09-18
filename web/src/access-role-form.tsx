import { useState } from "react";
import type { FormEvent } from "react";

import { createRole } from "./api";
import { Button } from "./components";
import type { PermissionSummary } from "./types";

type ApplyChange = (
  work: () => Promise<unknown>,
  done: string,
) => Promise<void>;

type CreateRoleFormProps = {
  apply: ApplyChange;
  busy: boolean;
  catalogue: PermissionSummary[];
  token: string;
};

// Render and manage the form for one new configurable role.
export function CreateRoleForm({
  apply,
  busy,
  catalogue,
  token,
}: CreateRoleFormProps) {
  const [draft, setDraft] = useState({
    code: "",
    title: "",
    description: "",
    permissions: [] as string[],
  });

  // Create one configurable role from the local draft.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await apply(
      () =>
        createRole(token, {
          code: draft.code.trim(),
          title: draft.title.trim(),
          description: draft.description.trim() || undefined,
          permissions: [...draft.permissions].sort(),
        }),
      `Created the ${draft.title.trim()} role.`,
    );
    setDraft({
      code: "",
      title: "",
      description: "",
      permissions: [],
    });
  }

  return (
    <form className="access-form" onSubmit={handleSubmit}>
      <h4>Create a role</h4>
      <label className="field" htmlFor="role-code">
        <span>Code</span>
        <small>Lowercase letters, digits, and underscores.</small>
        <input
          id="role-code"
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              code: event.target.value,
            }))
          }
          pattern="[a-z0-9_]{2,64}"
          required
          value={draft.code}
        />
      </label>
      <label className="field" htmlFor="role-title">
        <span>Title</span>
        <input
          id="role-title"
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              title: event.target.value,
            }))
          }
          required
          value={draft.title}
        />
      </label>
      <label className="field" htmlFor="role-description">
        <span>Description</span>
        <input
          id="role-description"
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              description: event.target.value,
            }))
          }
          value={draft.description}
        />
      </label>
      <fieldset className="access-scopes">
        <legend>Scopes</legend>
        {catalogue.map((permission) => (
          <label key={permission.code}>
            <input
              checked={draft.permissions.includes(permission.code)}
              disabled={busy}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  permissions: event.target.checked
                    ? [...current.permissions, permission.code].sort()
                    : current.permissions.filter(
                        (entry) => entry !== permission.code,
                      ),
                }))
              }
              type="checkbox"
            />
            <span className="mono">{permission.code}</span>
          </label>
        ))}
      </fieldset>
      <Button disabled={busy} type="submit">
        Create role
      </Button>
    </form>
  );
}
