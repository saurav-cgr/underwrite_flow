import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

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
import type { PermissionSummary, RoleRecord, UserRecord } from "./types";
import { roleLabelFor } from "./types";
import { Badge, Button, EmptyState, Panel } from "./components";

// Read one error into a message an administrator can act on.
function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

// Render the readable label for one stable role code.
function roleLabel(code: string): string {
  return roleLabelFor(code) ?? code;
}

// Give administrators control over users, roles, and permission scopes.
export function AccessAdministration({ token }: { token: string }) {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<RoleRecord[]>([]);
  const [catalogue, setCatalogue] = useState<PermissionSummary[]>([]);
  const [status, setStatus] = useState("");
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({
    email: "",
    displayName: "",
    password: "",
    roleId: "",
  });
  const [scopeDraft, setScopeDraft] = useState<Record<string, string[]>>({});
  const [roleDraft, setRoleDraft] = useState({
    code: "",
    title: "",
    description: "",
    permissions: [] as string[],
  });

  // Load users, roles, and the permission catalogue together.
  const load = useCallback(async () => {
    setProblem("");
    try {
      const [nextUsers, nextRoles, nextCatalogue] = await Promise.all([
        listUsers(token),
        listRoles(token),
        listPermissions(token),
      ]);
      setUsers(nextUsers);
      setRoles(nextRoles);
      setCatalogue(nextCatalogue);
      setScopeDraft(
        Object.fromEntries(
          nextRoles.map((role) => [role.id, [...role.permissions]]),
        ),
      );
    } catch (error) {
      setProblem(describe(error, "Access administration could not be loaded."));
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  // Run one administration change and refresh the visible state.
  async function apply(work: () => Promise<unknown>, done: string) {
    setBusy(true);
    setProblem("");
    setStatus("");
    try {
      await work();
      setStatus(done);
      await load();
    } catch (error) {
      setProblem(describe(error, "The change could not be saved."));
    } finally {
      setBusy(false);
    }
  }

  // Create one synthetic user from the draft form.
  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await apply(
      () =>
        createUser(token, {
          email: draft.email.trim(),
          display_name: draft.displayName.trim(),
          password: draft.password,
          role_id: draft.roleId || roles[0]?.id || "",
        }),
      `Created ${draft.email.trim()}.`,
    );
    setDraft((current) => ({
      ...current,
      email: "",
      displayName: "",
      password: "",
    }));
  }

  // Create one configurable role from the draft form.
  async function handleCreateRole(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await apply(
      () =>
        createRole(token, {
          code: roleDraft.code.trim(),
          title: roleDraft.title.trim(),
          description: roleDraft.description.trim() || undefined,
          permissions: [...roleDraft.permissions].sort(),
        }),
      `Created the ${roleDraft.title.trim()} role.`,
    );
    setRoleDraft({
      code: "",
      title: "",
      description: "",
      permissions: [],
    });
  }

  // Toggle one scope inside a role's draft scope list.
  function toggleScope(roleId: string, code: string, checked: boolean) {
    setScopeDraft((current) => {
      const existing = current[roleId] ?? [];
      return {
        ...current,
        [roleId]: checked
          ? [...new Set([...existing, code])].sort()
          : existing.filter((entry) => entry !== code),
      };
    });
  }

  return (
    <Panel title="Access administration">
      <p className="panel-note">
        Configure who can sign in and what each role may do. Scope changes take
        effect on the affected user&apos;s next request.
      </p>
      {problem ? (
        <p className="form-error" role="alert">
          {problem}
        </p>
      ) : null}
      <p aria-live="polite" className="panel-note" role="status">
        {status}
      </p>

      <section aria-labelledby="access-users-heading">
        <h3 id="access-users-heading">Users</h3>
        {users.length === 0 ? (
          <EmptyState
            title="No users loaded"
            detail="Seeded demo accounts appear here once the request succeeds."
          />
        ) : (
          <table className="access-table">
            <caption className="sr-only">
              Synthetic users, their role, and active state
            </caption>
            <thead>
              <tr>
                <th scope="col">Identity</th>
                <th scope="col">Role</th>
                <th scope="col">State</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>
                    <strong>{user.display_name}</strong>
                    <span className="mono">{user.email}</span>
                  </td>
                  <td>
                    <select
                      aria-label={`Role for ${user.email}`}
                      disabled={busy}
                      onChange={(event) =>
                        void apply(
                          () =>
                            updateUser(token, user.id, {
                              role_id: event.target.value,
                            }),
                          `Updated the role for ${user.email}.`,
                        )
                      }
                      value={user.role?.id ?? ""}
                    >
                      {user.role === null ? (
                        <option value="">No role assigned</option>
                      ) : null}
                      {roles.map((role) => (
                        <option key={role.id} value={role.id}>
                          {roleLabel(role.code)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <Badge tone={user.is_active ? "active" : "inactive"}>
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td>
                    <Button
                      disabled={busy}
                      onClick={() =>
                        void apply(
                          () =>
                            updateUser(token, user.id, {
                              is_active: !user.is_active,
                            }),
                          user.is_active
                            ? `Deactivated ${user.email}.`
                            : `Reactivated ${user.email}.`,
                        )
                      }
                      variant="quiet"
                    >
                      {user.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <form className="access-form" onSubmit={handleCreateUser}>
          <h4>Create a user</h4>
          <label className="field" htmlFor="access-email">
            <span>Email</span>
            <input
              id="access-email"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  email: event.target.value,
                }))
              }
              required
              type="email"
              value={draft.email}
            />
          </label>
          <label className="field" htmlFor="access-name">
            <span>Display name</span>
            <input
              id="access-name"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  displayName: event.target.value,
                }))
              }
              required
              value={draft.displayName}
            />
          </label>
          <label className="field" htmlFor="access-password">
            <span>Initial password</span>
            <input
              autoComplete="new-password"
              id="access-password"
              minLength={8}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
              required
              type="password"
              value={draft.password}
            />
          </label>
          <label className="field" htmlFor="access-role">
            <span>Role</span>
            <select
              id="access-role"
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  roleId: event.target.value,
                }))
              }
              required
              value={draft.roleId || roles[0]?.id || ""}
            >
              {roles.map((role) => (
                <option key={role.id} value={role.id}>
                  {roleLabel(role.code)}
                </option>
              ))}
            </select>
          </label>
          <Button disabled={busy} type="submit">
            Create user
          </Button>
        </form>
      </section>

      <section aria-labelledby="access-roles-heading">
        <h3 id="access-roles-heading">Roles</h3>
        {roles.map((role) => (
          <fieldset className="access-role" key={role.id}>
            <legend>
              {role.title}
              <span className="mono"> ({role.code})</span>
              {role.is_system ? <em> Seeded</em> : null}
            </legend>
            <p>
              <Badge tone={role.is_active ? "active" : "inactive"}>
                {role.is_active ? "Active" : "Inactive"}
              </Badge>
            </p>
            <div className="access-scopes">
              {catalogue.map((permission) => (
                <label key={permission.code}>
                  <input
                    checked={(scopeDraft[role.id] ?? []).includes(
                      permission.code,
                    )}
                    disabled={busy}
                    onChange={(event) =>
                      toggleScope(
                        role.id,
                        permission.code,
                        event.target.checked,
                      )
                    }
                    type="checkbox"
                  />
                  <span className="mono">{permission.code}</span>
                </label>
              ))}
            </div>
            <div className="access-role-actions">
              <Button
                disabled={busy}
                onClick={() =>
                  void apply(
                    () =>
                      updateRole(token, role.id, {
                        permissions: scopeDraft[role.id] ?? [],
                      }),
                    `Saved scopes for ${role.code}.`,
                  )
                }
                variant="quiet"
              >
                Save scopes
              </Button>
              <Button
                disabled={busy}
                onClick={() =>
                  void apply(
                    () =>
                      updateRole(token, role.id, {
                        is_active: !role.is_active,
                      }),
                    role.is_active
                      ? `Deactivated ${role.code}.`
                      : `Reactivated ${role.code}.`,
                  )
                }
                variant="quiet"
              >
                {role.is_active ? "Deactivate role" : "Reactivate role"}
              </Button>
            </div>
          </fieldset>
        ))}

        <form className="access-form" onSubmit={handleCreateRole}>
          <h4>Create a role</h4>
          <label className="field" htmlFor="role-code">
            <span>Code</span>
            <small>Lowercase letters, digits, and underscores.</small>
            <input
              id="role-code"
              onChange={(event) =>
                setRoleDraft((current) => ({
                  ...current,
                  code: event.target.value,
                }))
              }
              pattern="[a-z0-9_]{2,64}"
              required
              value={roleDraft.code}
            />
          </label>
          <label className="field" htmlFor="role-title">
            <span>Title</span>
            <input
              id="role-title"
              onChange={(event) =>
                setRoleDraft((current) => ({
                  ...current,
                  title: event.target.value,
                }))
              }
              required
              value={roleDraft.title}
            />
          </label>
          <label className="field" htmlFor="role-description">
            <span>Description</span>
            <input
              id="role-description"
              onChange={(event) =>
                setRoleDraft((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              value={roleDraft.description}
            />
          </label>
          <fieldset className="access-scopes">
            <legend>Scopes</legend>
            {catalogue.map((permission) => (
              <label key={permission.code}>
                <input
                  checked={roleDraft.permissions.includes(permission.code)}
                  disabled={busy}
                  onChange={(event) =>
                    setRoleDraft((current) => ({
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
      </section>
    </Panel>
  );
}
