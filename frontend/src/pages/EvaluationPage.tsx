import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FlaskConical, Play, Trash2, TriangleAlert } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingRows, LoadingState } from "@/components/common/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import type { EvaluationRun } from "@/lib/types";
import { cn, formatDateTime, formatPercent, titleCase, toneClasses } from "@/lib/utils";

const HEADLINE_METRICS = [
  "recall_at_5",
  "recall_at_10",
  "precision_at_5",
  "reciprocal_rank",
  "ndcg_at_10",
  "page_coverage",
  "keyword_coverage",
  "answer_correct",
  "refusal_correct",
  "citation_validity",
  "reference_f1",
];

const METRIC_DESCRIPTIONS: Record<string, string> = {
  recall_at_5: "Share of labelled source documents found in the top 5 candidates.",
  recall_at_10: "Share of labelled source documents found in the top 10 candidates.",
  precision_at_5: "Share of the top 5 candidates that are labelled sources.",
  reciprocal_rank: "Position of the first labelled source in the ranking.",
  ndcg_at_10: "Rank-weighted retrieval quality over the top 10.",
  page_coverage: "Share of labelled pages that were actually cited.",
  keyword_coverage: "Share of expected keywords present in the answer.",
  answer_correct: "Share of labelled facts present in the answer.",
  refusal_correct: "Share of unanswerable questions that were refused.",
  citation_validity: "Share of citations that resolved to a real page and passage.",
  reference_f1: "Overlap between the answer and the labelled reference answer.",
};

export function EvaluationPage() {
  const queryClient = useQueryClient();
  const [experiment, setExperiment] = useState("hybrid_rerank");
  const [maxQuestions, setMaxQuestions] = useState("10");
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);

  const experiments = useQuery({ queryKey: ["experiments"], queryFn: api.experiments });
  const dataset = useQuery({ queryKey: ["evaluation-dataset"], queryFn: api.evaluationDataset });
  const runs = useQuery({ queryKey: ["evaluation-runs"], queryFn: () => api.evaluationRuns({ limit: 25 }) });

  const runEvaluation = useMutation({
    mutationFn: () =>
      api.runEvaluation({
        experiments: [experiment],
        max_questions: maxQuestions === "all" ? undefined : Number(maxQuestions),
        top_k: 10,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["evaluation-runs"] }),
  });

  const deleteRun = useMutation({
    mutationFn: (id: string) => api.deleteEvaluationRun(id),
    onSuccess: () => {
      setSelectedRun(null);
      void queryClient.invalidateQueries({ queryKey: ["evaluation-runs"] });
    },
  });

  const detail = useQuery({
    queryKey: ["evaluation-run", selectedRun?.id],
    queryFn: () => api.evaluationRun(selectedRun!.id),
    enabled: Boolean(selectedRun?.id),
  });

  const selectedExperiment = (experiments.data ?? []).find((item) => item.name === experiment);
  const runsWithMetrics = (runs.data?.items ?? []).filter((run) => Object.keys(run.summary ?? {}).length > 0);
  const chartData = runsWithMetrics.slice(0, 8).reverse().map((run) => ({
    name: `${run.experiment}`,
    answer_correct: (run.summary.answer_correct as number) ?? null,
    refusal_correct: (run.summary.refusal_correct as number) ?? null,
    recall_at_5: (run.summary.recall_at_5 as number) ?? null,
  }));
  const chartHasValues = chartData.some(
    (row) => row.answer_correct !== null || row.refusal_correct !== null || row.recall_at_5 !== null,
  );

  return (
    <div className="space-y-5">
      <PageHeader
        title="Search quality"
        description="Measured with evaluation runs against the hand-labelled question set, the same title the navigation uses so a reader never has to guess which page they are on. Quality is only reported as measurements; a metric the dataset cannot support is reported as not evaluated, never as a score."
        meta={
          dataset.data ? (
            <>
              <span>
                Dataset {dataset.data.name} v{dataset.data.version}
              </span>
              <span>{dataset.data.question_count} questions</span>
              <span>{dataset.data.unanswerable_count} unanswerable</span>
              <span>{dataset.data.categories.length} categories</span>
            </>
          ) : null
        }
      />

      <section aria-labelledby="run-heading" className="rounded-lg border p-4">
        <h2 id="run-heading" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Run an experiment
        </h2>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="min-w-[240px] space-y-1.5">
            <Label>Experiment</Label>
            <Select value={experiment} onValueChange={setExperiment}>
              <SelectTrigger aria-label="Experiment">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(experiments.data ?? []).map((item) => (
                  <SelectItem key={item.name} value={item.name}>
                    {item.name}
                    {item.runnable ? "" : " (unavailable)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Questions</Label>
            <Select value={maxQuestions} onValueChange={setMaxQuestions}>
              <SelectTrigger className="w-[160px]" aria-label="Number of questions">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["5", "10", "22", "all"].map((value) => (
                  <SelectItem key={value} value={value}>
                    {value === "all" ? "all questions" : `first ${value}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            disabled={runEvaluation.isPending || selectedExperiment?.runnable === false}
            onClick={() => runEvaluation.mutate()}
          >
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            {runEvaluation.isPending ? "Running" : "Run experiment"}
          </Button>
        </div>

        {selectedExperiment ? (
          <p className="mt-3 text-xs text-muted-foreground">
            {selectedExperiment.description}
            {selectedExperiment.requires.length > 0 ? ` Requires: ${selectedExperiment.requires.join(", ")}.` : ""}
          </p>
        ) : null}

        {selectedExperiment && !selectedExperiment.runnable ? (
          <p className="mt-2 flex items-start gap-2 rounded-md border border-warning/35 bg-warning/5 p-2.5 text-xs">
            <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" aria-hidden="true" />
            {selectedExperiment.unavailable_reason ?? "This experiment cannot run on the current deployment."}
          </p>
        ) : null}

        {runEvaluation.isError ? <div className="mt-3"><ErrorState error={runEvaluation.error} /></div> : null}
        {runEvaluation.isPending ? <LoadingState label="Running the labelled questions through the pipeline" /> : null}
      </section>

      <Tabs defaultValue="runs">
        <TabsList>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="experiments">
            <FlaskConical className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Experiments and dataset
          </TabsTrigger>
        </TabsList>

        <TabsContent value="runs" className="space-y-4">
          {runs.isError ? <ErrorState error={runs.error} onRetry={() => void runs.refetch()} /> : null}
          {runs.isLoading ? <LoadingRows rows={4} /> : null}

          {runs.data && runs.data.items.length === 0 ? (
            <EmptyState
              title="No evaluation run yet"
              description="Run an experiment above. Its metrics are stored with the run so later results can be compared against it."
            />
          ) : null}

          {chartHasValues ? (
            <figure className="rounded-lg border p-4">
              <figcaption className="text-xs font-medium">Headline metrics per run</figcaption>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                Only runs that produced a value for at least one of these metrics are plotted. A bar that is absent means
                the metric was not evaluated for that run.
              </p>
              <div className="mt-3 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="name" fontSize={11} stroke="hsl(var(--muted-foreground))" />
                    <YAxis domain={[0, 1]} fontSize={11} stroke="hsl(var(--muted-foreground))" tickFormatter={(value) => `${Math.round(Number(value) * 100)}%`} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <ChartTooltip
                      formatter={(value) =>
                        value === null || value === undefined ? "not evaluated" : formatPercent(Number(value), 0)
                      }
                      contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }}
                    />
                    <Bar dataKey="recall_at_5" name="recall@5" fill="hsl(var(--primary))" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="answer_correct" name="answer correctness" fill="hsl(var(--success))" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="refusal_correct" name="refusal correctness" fill="hsl(var(--warning))" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </figure>
          ) : null}

          {runs.data && runs.data.items.length > 0 ? (
            <div className="rounded-lg border">
              <Table>
                <caption className="sr-only">Stored evaluation runs with their measured headline metrics.</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Run</TableHead>
                    <TableHead scope="col">Status</TableHead>
                    <TableHead scope="col" className="text-right">
                      Questions
                    </TableHead>
                    {HEADLINE_METRICS.slice(0, 5).map((metric) => (
                      <TableHead key={metric} scope="col" className="text-right">
                        {metric}
                      </TableHead>
                    ))}
                    <TableHead scope="col" className="text-right">
                      Actions
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.data.items.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="text-xs">
                        <span className="font-medium">{run.experiment}</span>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">{formatDateTime(run.created_at)}</p>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn(
                            "font-normal",
                            toneClasses(
                              run.status === "completed" ? "success" : run.status === "unavailable" ? "warning" : "danger",
                            ),
                          )}
                        >
                          {titleCase(run.status)}
                        </Badge>
                        {run.error_message ? (
                          <p className="mt-1 max-w-[220px] text-[11px] text-muted-foreground">{run.error_message}</p>
                        ) : null}
                      </TableCell>
                      <TableCell className="tnum text-right text-xs">{run.question_count}</TableCell>
                      {HEADLINE_METRICS.slice(0, 5).map((metric) => {
                        const value = run.summary[metric];
                        return (
                          <TableCell key={metric} className="tnum text-right text-xs">
                            {value === null || value === undefined ? (
                              <span className="italic text-muted-foreground">not evaluated</span>
                            ) : (
                              formatPercent(value as number, 0)
                            )}
                          </TableCell>
                        );
                      })}
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setSelectedRun(run)}>
                            Detail
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Delete run ${run.experiment}`}
                            disabled={deleteRun.isPending}
                            onClick={() => deleteRun.mutate(run.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : null}

          {detail.data ? (
            <div className="rounded-lg border">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5">
                <h3 className="text-xs font-medium">
                  Per-question results · {detail.data.experiment} · {detail.data.results?.length ?? 0} question(s)
                </h3>
                <span className="text-[11px] text-muted-foreground">
                  {formatDateTime(detail.data.started_at)} to {formatDateTime(detail.data.finished_at)}
                </span>
              </div>
              <Table>
                <caption className="sr-only">Per-question metrics for the selected run.</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Question</TableHead>
                    <TableHead scope="col">Category</TableHead>
                    <TableHead scope="col">Answer status</TableHead>
                    <TableHead scope="col" className="text-right">
                      Keywords found
                    </TableHead>
                    <TableHead scope="col" className="text-right">
                      Refusal correct
                    </TableHead>
                    <TableHead scope="col" className="text-right">
                      Latency
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(detail.data.results ?? []).map((result) => {
                    const found = (result.metrics.keywords_found as string[] | undefined)?.length ?? 0;
                    const missing = (result.metrics.keywords_missing as string[] | undefined)?.length ?? 0;
                    return (
                      <TableRow key={result.id}>
                        <TableCell className="max-w-[320px] text-xs">
                          <p className="font-medium">{result.question}</p>
                          {result.error ? <p className="mt-0.5 text-destructive">{result.error}</p> : null}
                        </TableCell>
                        <TableCell className="text-xs">{result.category ?? "not categorised"}</TableCell>
                        <TableCell className="text-xs">{result.answer_status ?? "not recorded"}</TableCell>
                        <TableCell className="tnum text-right text-xs">
                          {found} of {found + missing}
                        </TableCell>
                        <TableCell className="text-right text-xs">
                          {result.metrics.refusal_correct === null || result.metrics.refusal_correct === undefined
                            ? "not evaluated"
                            : result.metrics.refusal_correct
                              ? "yes"
                              : "no"}
                        </TableCell>
                        <TableCell className="tnum text-right text-xs">
                          {result.latency_ms !== null ? `${result.latency_ms} ms` : "not timed"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : null}

          {detail.isError ? <ErrorState error={detail.error} /> : null}
        </TabsContent>

        <TabsContent value="experiments" className="space-y-4">
          <section aria-labelledby="experiments-heading" className="rounded-lg border">
            <h2 id="experiments-heading" className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              What can be measured on this deployment
            </h2>
            <Table>
              <caption className="sr-only">Available experiments and whether they can run here.</caption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Experiment</TableHead>
                  <TableHead scope="col">Description</TableHead>
                  <TableHead scope="col">Requires</TableHead>
                  <TableHead scope="col">Runnable</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(experiments.data ?? []).map((item) => (
                  <TableRow key={item.name}>
                    <TableCell className="text-xs font-medium">{item.name}</TableCell>
                    <TableCell className="max-w-[320px] text-xs text-muted-foreground">{item.description}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {item.requires.length > 0 ? item.requires.join(", ") : "nothing beyond the base stack"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {item.runnable ? (
                        <Badge variant="outline" className={cn("font-normal", toneClasses("success"))}>
                          Runnable
                        </Badge>
                      ) : (
                        <>
                          <Badge variant="outline" className={cn("font-normal", toneClasses("warning"))}>
                            Cannot run
                          </Badge>
                          {item.unavailable_reason ? (
                            <p className="mt-1 max-w-[240px] text-[11px] text-muted-foreground">{item.unavailable_reason}</p>
                          ) : null}
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>

          <section aria-labelledby="metric-notes" className="rounded-lg border p-4">
            <h2 id="metric-notes" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              How to read a metric
            </h2>
            <dl className="mt-3 grid gap-x-8 gap-y-2 text-xs sm:grid-cols-2">
              {Object.entries(METRIC_DESCRIPTIONS).map(([metric, description]) => (
                <div key={metric} className="border-b border-border/70 pb-1.5">
                  <dt className="font-mono text-[11px] font-medium">{metric}</dt>
                  <dd className="mt-0.5 text-muted-foreground">{description}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
              A null metric means the dataset carries no ground truth for it, so it is excluded from the average instead
              of being counted as zero. Where an experiment needs a language model and none is configured, the run says
              it cannot execute rather than approximating a score.
            </p>
          </section>

          <section aria-labelledby="dataset-heading" className="rounded-lg border">
            <h2 id="dataset-heading" className="border-b px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Labelled question set
            </h2>
            {dataset.isLoading ? (
              <div className="p-4">
                <LoadingRows rows={6} />
              </div>
            ) : (
              <Table>
                <caption className="sr-only">Golden dataset questions with their ground truth.</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">ID</TableHead>
                    <TableHead scope="col">Question</TableHead>
                    <TableHead scope="col">Category</TableHead>
                    <TableHead scope="col">Ground truth</TableHead>
                    <TableHead scope="col">Unanswerable</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(dataset.data?.questions ?? []).map((question) => (
                    <TableRow key={question.id}>
                      <TableCell className="font-mono text-[11px]">{question.id}</TableCell>
                      <TableCell className="max-w-[320px] text-xs">{question.question}</TableCell>
                      <TableCell className="text-xs">{question.category}</TableCell>
                      <TableCell className="max-w-[260px] text-xs text-muted-foreground">
                        {question.expected_keywords.length > 0
                          ? question.expected_keywords.join(", ")
                          : (question.expected_answer ?? "must be refused")}
                      </TableCell>
                      <TableCell className="text-xs">{question.is_unanswerable ? "yes" : "no"}</TableCell>
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
