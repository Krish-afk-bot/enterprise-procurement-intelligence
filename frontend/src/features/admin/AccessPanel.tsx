import { useQuery } from "@tanstack/react-query";

import { ErrorState, LoadingRows } from "@/components/common/States";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { plural, titleCase } from "@/lib/utils";
import { useAuth } from "@/store/auth";

/** The signed-in account and the access model the API enforces. */
export function AccessPanel() {
  const user = useAuth((state) => state.user);
  const accessModel = useQuery({ queryKey: ["access-model"], queryFn: api.accessModel });

  return (
    <>
      <section className="rounded-lg border p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Signed-in account</h2>
        <dl className="mt-2 grid gap-x-6 gap-y-1.5 text-xs sm:grid-cols-2">
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted-foreground">Account</dt>
            <dd className="font-medium">{user?.full_name || user?.email}</dd>
          </div>
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted-foreground">Role</dt>
            <dd className="font-medium">{titleCase(user?.role)}</dd>
          </div>
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted-foreground">Document access ceiling</dt>
            <dd className="font-medium">{titleCase(user?.access_ceiling)}</dd>
          </div>
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted-foreground">Permissions</dt>
            <dd className="font-medium">{plural(user?.permissions.length ?? 0, "permission")}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border">
        <h2 className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Access model enforced by the API
        </h2>

        {accessModel.isError ? (
          <div className="p-4">
            <ErrorState error={accessModel.error} onRetry={() => void accessModel.refetch()} />
          </div>
        ) : accessModel.isLoading ? (
          <div className="p-4">
            <LoadingRows rows={5} />
          </div>
        ) : (
          <>
            <Table>
              <caption className="sr-only">Roles, the permissions each role holds and the document access ceiling.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Role</TableHead>
                  <TableHead scope="col">Document access ceiling</TableHead>
                  <TableHead scope="col" className="text-right">
                    Permissions
                  </TableHead>
                  <TableHead scope="col">Holds</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(accessModel.data?.roles ?? []).map((role) => {
                  const permissions = accessModel.data?.role_permissions[role] ?? [];
                  return (
                    <TableRow key={role}>
                      <TableCell className="text-xs font-medium">{titleCase(role)}</TableCell>
                      <TableCell className="text-xs">
                        {titleCase(accessModel.data?.role_access_ceiling[role] ?? "not recorded")}
                      </TableCell>
                      <TableCell className="tnum text-right text-xs">{permissions.length}</TableCell>
                      <TableCell className="text-[11px] text-muted-foreground">
                        {permissions.join(", ") || "none"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
            {accessModel.data?.note ? (
              <p className="border-t px-4 py-2.5 text-[11px] leading-relaxed text-muted-foreground">
                {accessModel.data.note}
              </p>
            ) : null}
          </>
        )}
      </section>

      <section className="rounded-lg border p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Account management</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          This build exposes no user-administration API. Accounts are created with the deployment CLI
          (<code className="font-mono text-[11px]">python -m app.cli create-user</code>) and there is no endpoint that
          lists, edits, suspends or deletes accounts. The interface therefore shows the access model rather than
          offering controls that would not be persisted.
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          Document access levels a checklist can assign:{" "}
          <span className="font-medium text-foreground">{(accessModel.data?.access_levels ?? []).map(titleCase).join(", ") || "not reported"}</span>.
        </p>
      </section>
    </>
  );
}
