import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Cpu, FileStack, Gauge, Route, ShieldCheck, Users } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { SystemStatusPanel } from "@/components/common/SystemStatus";
import { EmptyState, ErrorState, LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import {
  activityLabel,
  cn,
  documentLifecycle,
  formatDateTime,
  formatNumber,
  plural,
  titleCase,
  toneClasses,
} from "@/lib/utils";
import { useAuth } from "@/store/auth";

export function AdminPage() {
  const user = useAuth((state) => state.user);
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: api.stats });
  const indexing = useQuery({ queryKey: ["indexing"], queryFn: api.indexing, refetchInterval: 15_000 });
  const accessModel = useQuery({ queryKey: ["access-model"], queryFn: api.accessModel });
  const config = useQuery({ queryKey: ["model-config"], queryFn: api.modelConfig });
  const routing = useQuery({ queryKey: ["routing"], queryFn: api.routing });
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => api.audit({ limit: 50 }) });
  const traces = useQuery({ queryKey: ["traces"], queryFn: () => api.traces({ limit: 25 }) });
  const health = useQuery({ queryKey: ["admin-health"], queryFn: api.health, refetchInterval: 30_000 });
  const failed = useQuery({
    queryKey: ["documents", "admin-failed"],
    queryFn: () => api.documents({ status: "failed", limit: 50 }),
  });
  const processing = useQuery({
    queryKey: ["documents", "admin-processing"],
    queryFn: () => api.documents({ status: "processing", limit: 50 }),
  });

  const data = stats.data;
  const modelConfig = config.data;

  const components = modelConfig
    ? [
        {
          label: "Answer generation",
          value: modelConfig.llm_model ?? "not configured",
          detail: `provider ${modelConfig.llm_provider}${
            modelConfig.llm_base_url_host ? ` · endpoint host ${modelConfig.llm_base_url_host}` : ""
          }`,
          state: modelConfig.llm_configured
            ? { label: "Configured", tone: "success" as const }
            : { label: "Not configured · answers composed from evidence", tone: "warning" as const },
        },
        {
          label: "Page imagery model",
          value: modelConfig.vlm_model ?? "not configured",
          detail: `escalation ${modelConfig.vision_escalation_enabled ? "enabled" : "disabled"}`,
          state: modelConfig.vlm_configured
            ? { label: "Configured", tone: "success" as const }
            : { label: "Not configured · OCR only", tone: "warning" as const },
        },
        {
          label: "Embedding model",
          value: modelConfig.embedding_model,
          detail: `${modelConfig.embedding_provider} · device ${modelConfig.embedding_device ?? "auto"}`,
          state: { label: "Active", tone: "success" as const },
        },
        {
          label: "Evidence selection model",
          value: modelConfig.reranker_model ?? "disabled",
          detail: `${modelConfig.reranker_provider} · enabled ${modelConfig.reranker_enabled}`,
          state: modelConfig.reranker_enabled
            ? { label: "Active", tone: "success" as const }
            : { label: "Disabled", tone: "neutral" as const },
        },
        {
          label: "OCR",
          value: modelConfig.ocr_enabled ? "enabled" : "disabled",
          detail: "governs pages without a text layer",
          state: modelConfig.ocr_enabled
            ? { label: "Active", tone: "success" as const }
            : { label: "Disabled", tone: "neutral" as const },
        },
        {
          label: "Correction loop",
          value: `max ${modelConfig.max_agent_iterations} corrective iterations`,
          detail: "upper bound on the retrieval loop",
          state: { label: "Bounded", tone: "neutral" as const },
        },
      ]
    : [];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Administration"
        description="Document governance, accounts and access, search and answer quality, activity, and the models this deployment actually runs. This area is limited to administrator accounts."
      />

      {stats.isError ? <ErrorState error={stats.error} onRetry={() => void stats.refetch()} /> : null}

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">
            <Gauge className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="governance">
            <FileStack className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Documents &amp; governance
          </TabsTrigger>
          <TabsTrigger value="access">
            <Users className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Users &amp; access
          </TabsTrigger>
          <TabsTrigger value="quality">
            <ShieldCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Search &amp; answer quality
          </TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="configuration">
            <Cpu className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            System health &amp; configuration
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {stats.isLoading || !data ? (
            <LoadingRows rows={6} />
          ) : (
            <>
              <section aria-labelledby="workspace-figures" className="rounded-lg border">
                <h2 id="workspace-figures" className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Workspace at a glance
                </h2>
                <dl className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    { label: "Documents indexed", value: data.documents_indexed },
                    { label: "Documents processing", value: data.documents_pending },
                    { label: "Documents failed", value: data.documents_failed },
                    { label: "Pages extracted", value: data.pages },
                    { label: "Suppliers", value: data.suppliers },
                    { label: "Contracts", value: data.contracts },
                    { label: "Price rows", value: data.prices },
                    { label: "Compliance certificates", value: data.compliance_certificates },
                    { label: "Extracted tables", value: data.tables },
                    { label: "Relationship nodes", value: data.graph_nodes },
                    { label: "Relationship edges", value: data.graph_edges },
                    { label: "Evaluation runs", value: data.evaluation_runs },
                  ].map((figure) => (
                    <div key={figure.label} className="bg-card p-4">
                      <dt className="text-xs text-muted-foreground">{figure.label}</dt>
                      <dd className="tnum mt-1 text-lg font-semibold tracking-tight">{formatNumber(figure.value)}</dd>
                    </div>
                  ))}
                </dl>
              </section>

              <section className="rounded-lg border p-4">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Ingestion queue</h2>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Uploads are queued and processed by a background worker outside the request path.
                </p>
                {indexing.isError ? (
                  <ErrorState error={indexing.error} onRetry={() => void indexing.refetch()} />
                ) : (
                  <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {(["queued", "running", "succeeded", "failed"] as const).map((key) => (
                      <div key={key}>
                        <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{key}</dt>
                        <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(Number(indexing.data?.[key] ?? 0))}</dd>
                      </div>
                    ))}
                  </dl>
                )}
                {(indexing.data?.notes ?? []).length > 0 ? (
                  <ul className="mt-3 space-y-1 border-t pt-3 text-[11px] text-muted-foreground">
                    {(indexing.data?.notes ?? []).map((note, index) => (
                      <li key={index}>{note}</li>
                    ))}
                  </ul>
                ) : null}
              </section>
            </>
          )}
        </TabsContent>

        <TabsContent value="governance" className="space-y-4">
          <section className="rounded-lg border">
            <h2 className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Documents that need attention
            </h2>
            {failed.isLoading || processing.isLoading ? (
              <div className="p-4">
                <LoadingRows rows={3} />
              </div>
            ) : (failed.data?.items.length ?? 0) + (processing.data?.items.length ?? 0) === 0 ? (
              <div className="p-4">
                <EmptyState
                  icon={FileStack}
                  title="Nothing is stuck"
                  description="No document is in a failed or in-flight processing state. Every uploaded file has finished processing."
                />
              </div>
            ) : (
              <Table>
                <caption className="sr-only">Documents that failed processing or are still being processed.</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Document</TableHead>
                    <TableHead scope="col">State</TableHead>
                    <TableHead scope="col">Stage</TableHead>
                    <TableHead scope="col">Recorded error</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[...(failed.data?.items ?? []), ...(processing.data?.items ?? [])].map((document) => {
                    const lifecycle = documentLifecycle(document);
                    return (
                      <TableRow key={document.id}>
                        <TableCell>
                          <Link to={`/documents/${document.id}`} className="text-xs font-medium hover:underline">
                            {document.title || document.filename}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn("font-normal", toneClasses(lifecycle.tone))}>
                            {lifecycle.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{document.stage ?? "not reported"}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{document.error_message ?? "none recorded"}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Governance this build enforces</h2>
            <ul className="mt-2 space-y-1.5 text-xs text-muted-foreground">
              <li>
                <span className="font-medium text-foreground">Document access levels.</span> Every document carries an access
                level and every role has a ceiling; retrieval is filtered by tenant and by readable access level before a
                candidate can reach a model.
              </li>
              <li>
                <span className="font-medium text-foreground">Every metadata change is recorded.</span> Document uploads,
                detail edits, re-indexing and deletions are written to the audit log with the acting account and the
                before/after values.
              </li>
              <li>
                <span className="font-medium text-foreground">Versions are preserved.</span> Uploading a new version links the
                replaced document to its successor; the earlier version keeps its own pages, text and citations.
              </li>
              <li>
                <span className="font-medium text-foreground">Processing state is reported, not editable.</span> Status, stage
                and progress come from the ingestion run; a person cannot set them.
              </li>
              <li>
                <span className="font-medium text-foreground">No retention or legal-hold policy is implemented</span> in this
                build, and no archive action is exposed. Deletion removes the file and everything derived from it.
              </li>
            </ul>
          </section>
        </TabsContent>

        <TabsContent value="access" className="space-y-4">
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
        </TabsContent>

        <TabsContent value="quality" className="space-y-4">
          <section className="rounded-lg border p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Questions asked</h2>
            <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Questions run</dt>
                <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(data?.queries_total ?? 0)}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Answered with evidence</dt>
                <dd className="tnum mt-0.5 text-lg font-semibold">
                  {formatNumber((data?.queries_total ?? 0) - (data?.queries_insufficient_evidence ?? 0))}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Unable to verify</dt>
                <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(data?.queries_insufficient_evidence ?? 0)}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Evaluation runs</dt>
                <dd className="tnum mt-0.5 text-lg font-semibold">{formatNumber(data?.evaluation_runs ?? 0)}</dd>
              </div>
            </dl>
            <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
              Answer and retrieval quality are only reported as runs of the evaluation suite over the labelled question
              set; they are never estimated. Open the{" "}
              <Link to="/evaluation" className="underline hover:text-foreground">
                Search quality
              </Link>{" "}
              view for the per-experiment results.
            </p>
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Query execution traces</h2>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Each step the pipeline took for a question, with the node that produced it. This is the same path the answer
              view summarises as &ldquo;how the answer was verified&rdquo;.
            </p>
            <div className="mt-3 space-y-3">
              {traces.isLoading ? <LoadingRows rows={3} /> : null}
              {(traces.data?.items ?? []).map((trace) => (
                <article key={trace.id} className="rounded-lg border p-3">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                    <Badge variant="outline" className="font-mono font-normal">
                      query {String(trace.query_id ?? trace.id).slice(0, 8)}
                    </Badge>
                    <span className="tnum">{trace.duration_ms !== null ? `${trace.duration_ms} ms` : "not timed"}</span>
                    <span>{trace.iterations ?? 0} iteration(s)</span>
                    <span className="ml-auto">{formatDateTime(trace.created_at)}</span>
                  </div>
                  <ol className="mt-2 space-y-1">
                    {(trace.events ?? []).map((event, index) => (
                      <li key={index} className="grid grid-cols-[auto_minmax(0,1fr)] gap-2 text-[11px]">
                        <span className="h-fit rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                          {event.node}
                        </span>
                        <span className="min-w-0">
                          <span className="font-medium">{event.event}</span>
                          {event.detail ? <span className="text-muted-foreground"> {event.detail}</span> : null}
                        </span>
                      </li>
                    ))}
                  </ol>
                </article>
              ))}
              {traces.data && traces.data.items.length === 0 ? (
                <p className="rounded-lg border border-dashed p-4 text-xs text-muted-foreground">
                  No trace has been recorded yet. A trace is written for each question the pipeline processes.
                </p>
              ) : null}
            </div>
          </section>
        </TabsContent>

        <TabsContent value="activity">
          <section className="rounded-lg border">
            <h2 className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Recorded activity
            </h2>
            <p className="px-4 py-2.5 text-[11px] leading-relaxed text-muted-foreground">
              Questions, uploads, document reads, detail edits, comparisons and evaluation runs are recorded with the actor,
              the resource and the request id. The raw action name is kept beside the plain-language label.
            </p>
            {audit.isError ? (
              <div className="p-4">
                <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
              </div>
            ) : audit.isLoading ? (
              <div className="p-4">
                <LoadingRows rows={6} />
              </div>
            ) : (
              <Table>
                <caption className="sr-only">Recorded actions in this workspace.</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">When</TableHead>
                    <TableHead scope="col">What happened</TableHead>
                    <TableHead scope="col">Resource</TableHead>
                    <TableHead scope="col">Outcome</TableHead>
                    <TableHead scope="col">Request</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(audit.data?.items ?? []).map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="text-xs text-muted-foreground">{formatDateTime(entry.created_at)}</TableCell>
                      <TableCell className="text-xs font-medium">
                        {activityLabel(entry.action)}
                        <span className="ml-2 font-mono text-[10px] text-muted-foreground">{entry.action}</span>
                      </TableCell>
                      <TableCell className="text-xs">
                        {entry.resource_type ?? "not recorded"}
                        {entry.resource_id ? (
                          <span className="ml-1 font-mono text-[11px] text-muted-foreground">{entry.resource_id.slice(0, 8)}</span>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-xs">{entry.outcome ?? "success"}</TableCell>
                      <TableCell className="font-mono text-[10px] text-muted-foreground">
                        {entry.request_id ? entry.request_id.slice(0, 12) : "not recorded"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </section>
        </TabsContent>

        <TabsContent value="configuration" className="space-y-4">
          <section className="rounded-lg border p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Provider status</h2>
            <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
              Reported by the health endpoint of the running API. A provider that is not available is shown as unavailable,
              and the answer pipeline states why it degraded rather than hiding it.
            </p>
            <div className="mt-3">
              <SystemStatusPanel health={health.data} />
            </div>
            <dl className="mt-4 grid gap-x-6 gap-y-1.5 border-t pt-3 text-[11px] sm:grid-cols-2">
              {Object.entries(health.data?.providers ?? {}).map(([kind, status]) => (
                <div key={kind} className="flex items-baseline justify-between gap-3 border-b border-border/60 pb-1">
                  <dt className="text-muted-foreground">
                    {kind} · {status.name}
                  </dt>
                  <dd className={cn("font-medium", status.available ? "text-success" : "text-destructive")}>
                    {status.available ? "available" : "unavailable"}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="rounded-lg border">
            <h2 className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Model and engine components
            </h2>
            {config.isError ? (
              <div className="p-4">
                <ErrorState error={config.error} onRetry={() => void config.refetch()} />
              </div>
            ) : config.isLoading ? (
              <div className="p-4">
                <LoadingRows rows={6} />
              </div>
            ) : (
              <Table>
                <caption className="sr-only">Components of the pipeline and whether each is configured.</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Component</TableHead>
                    <TableHead scope="col">Configured value</TableHead>
                    <TableHead scope="col">Detail</TableHead>
                    <TableHead scope="col">State</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {components.map((component) => (
                    <TableRow key={component.label}>
                      <TableCell className="text-xs font-medium">{component.label}</TableCell>
                      <TableCell className="text-xs">{component.value}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{component.detail}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={cn("font-normal", toneClasses(component.state.tone))}>
                          {component.state.label}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {(modelConfig?.notes ?? []).length > 0 ? (
              <ul className="space-y-1 border-t px-4 py-3 text-xs text-muted-foreground">
                {(modelConfig?.notes ?? []).map((note, index) => (
                  <li key={index} className="border-l pl-3">
                    {note}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>

          <section className="rounded-lg border">
            <h2 className="flex items-center gap-2 border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Route className="h-3.5 w-3.5" aria-hidden="true" />
              Which engine handles which task
            </h2>
            <p className="px-4 py-2.5 text-[11px] leading-relaxed text-muted-foreground">
              Deterministic engines appear alongside the models. Exact arithmetic, aggregation and version comparison are
              never delegated to a language model.
            </p>
            {routing.isLoading ? (
              <div className="p-4">
                <LoadingRows rows={8} />
              </div>
            ) : (
              <Table>
                <caption className="sr-only">Tasks with the engine that handles each one.</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Task</TableHead>
                    <TableHead scope="col">Engine</TableHead>
                    <TableHead scope="col">Model</TableHead>
                    <TableHead scope="col">Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(routing.data ?? []).map((row) => (
                    <TableRow key={row.task}>
                      <TableCell className="text-xs font-medium">{row.task}</TableCell>
                      <TableCell className="text-xs">
                        <Badge variant="outline" className="font-normal">
                          {row.engine}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">{row.model ?? "deterministic"}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{row.reason}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </section>
        </TabsContent>
      </Tabs>
    </div>
  );
}
