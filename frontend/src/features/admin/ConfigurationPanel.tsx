import { useQuery } from "@tanstack/react-query";
import { Route } from "lucide-react";

import { SystemStatusPanel } from "@/components/common/SystemStatus";
import { ErrorState, LoadingRows } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { cn, toneClasses } from "@/lib/utils";

/** Provider status, the configured models and the engine routing table. */
export function ConfigurationPanel() {
  const config = useQuery({ queryKey: ["model-config"], queryFn: api.modelConfig });
  const routing = useQuery({ queryKey: ["routing"], queryFn: api.routing });
  const health = useQuery({ queryKey: ["admin-health"], queryFn: api.health, refetchInterval: 30_000 });
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
    <>
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
    </>
  );
}
