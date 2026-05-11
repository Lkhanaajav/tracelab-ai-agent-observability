import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Code2,
  GitCompare,
  ListChecks,
  PlayCircle,
  XCircle,
} from "lucide-react";
import "./styles.css";

const API = "http://127.0.0.1:8000";

type Run = {
  id: string;
  task_id: string;
  task_name: string;
  agent_name: string;
  model: string;
  status: "passed" | "failed";
  total_latency_ms: number;
  total_tokens: number;
  estimated_cost_usd: number;
  final_output: string;
  average_score: number;
  failed_metrics: number;
};

type TraceEvent = {
  id: string;
  sequence_index: number;
  event_type: string;
  name: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  latency_ms: number;
  token_count: number;
  created_at: string;
};

type EvalResult = {
  id: string;
  metric_name: string;
  score: number;
  passed: number;
  explanation: string;
};

type RunDetail = Run & {
  task_input: string;
  expected_behavior: string;
  eval_config: Record<string, unknown>;
  events: TraceEvent[];
  evals: EvalResult[];
};

type Regression = {
  task_id: string;
  latest: Run;
  baseline: Run;
  delta: {
    score: number;
    latency_ms: number;
    cost_usd: number;
    tokens: number;
  };
};

function formatCost(value: number) {
  return `$${value.toFixed(3)}`;
}

function formatScore(value?: number) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function StatusPill({ status }: { status: Run["status"] }) {
  const passed = status === "passed";
  return (
    <span className={`pill ${passed ? "pillPass" : "pillFail"}`}>
      {passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
      {status}
    </span>
  );
}

function MetricCard({
  label,
  value,
  icon,
  tone = "neutral",
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  tone?: "neutral" | "good" | "bad";
}) {
  return (
    <div className={`metric metric-${tone}`}>
      <div className="metricIcon">{icon}</div>
      <div>
        <div className="metricLabel">{label}</div>
        <div className="metricValue">{value}</div>
      </div>
    </div>
  );
}

function RunsTable({
  runs,
  selected,
  onSelect,
}: {
  runs: Run[];
  selected?: string;
  onSelect: (run: Run) => void;
}) {
  return (
    <section className="panel runsPanel">
      <div className="panelHeader">
        <div>
          <h2>Agent Runs</h2>
          <p>Recent traces with eval scores, latency, and cost.</p>
        </div>
        <PlayCircle size={22} />
      </div>
      <div className="runList">
        {runs.map((run) => (
          <button
            className={`runRow ${selected === run.id ? "runRowActive" : ""}`}
            key={run.id}
            onClick={() => onSelect(run)}
          >
            <div>
              <div className="runTitle">{run.task_name}</div>
              <div className="runMeta">{run.id} | {run.model}</div>
            </div>
            <div className="runRight">
              <StatusPill status={run.status} />
              <strong>{formatScore(run.average_score)}</strong>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function TraceTimeline({
  events,
  selected,
  onSelect,
}: {
  events: TraceEvent[];
  selected?: string;
  onSelect: (event: TraceEvent) => void;
}) {
  return (
    <div className="timeline">
      {events.map((event) => (
        <button
          key={event.id}
          className={`timelineItem ${selected === event.id ? "timelineActive" : ""}`}
          onClick={() => onSelect(event)}
        >
          <span className="timelineIndex">{event.sequence_index}</span>
          <span>
            <strong>{event.name}</strong>
            <small>{event.event_type} | {event.latency_ms} ms | {event.token_count} tok</small>
          </span>
        </button>
      ))}
    </div>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="jsonBlock">{JSON.stringify(value, null, 2)}</pre>;
}

function RunDetailView({ detail }: { detail: RunDetail }) {
  const [eventId, setEventId] = useState<string | undefined>(detail.events[0]?.id);
  useEffect(() => {
    setEventId(detail.events[0]?.id);
  }, [detail.id, detail.events]);

  const selectedEvent = detail.events.find((event) => event.id === eventId) ?? detail.events[0];
  const failed = detail.evals.filter((item) => !item.passed);

  return (
    <section className="detail">
      <div className="detailHeader">
        <div>
          <div className="eyebrow">Run Detail</div>
          <h1>{detail.task_name}</h1>
          <p>{detail.task_input}</p>
        </div>
        <StatusPill status={detail.status} />
      </div>

      <div className="metricsGrid">
        <MetricCard label="Eval Score" value={formatScore(detail.average_score)} icon={<ListChecks />} tone={failed.length ? "bad" : "good"} />
        <MetricCard label="Latency" value={`${detail.total_latency_ms} ms`} icon={<Clock3 />} />
        <MetricCard label="Cost" value={formatCost(detail.estimated_cost_usd)} icon={<CircleDollarSign />} />
        <MetricCard label="Tokens" value={String(detail.total_tokens)} icon={<Code2 />} />
      </div>

      <div className="twoColumn">
        <div className="panel">
          <div className="panelHeader">
            <div>
              <h2>Trace Timeline</h2>
              <p>Prompt, tool calls, observations, and final output.</p>
            </div>
            <Activity size={22} />
          </div>
          <TraceTimeline events={detail.events} selected={selectedEvent?.id} onSelect={setEventIdFromEvent(setEventId)} />
        </div>

        <div className="panel">
          <div className="panelHeader">
            <div>
              <h2>Event Inspector</h2>
              <p>{selectedEvent?.name ?? "No event selected"}</p>
            </div>
            <Code2 size={22} />
          </div>
          {selectedEvent ? (
            <div className="inspector">
              <h3>Input</h3>
              <JsonBlock value={selectedEvent.input_json} />
              <h3>Output</h3>
              <JsonBlock value={selectedEvent.output_json} />
            </div>
          ) : null}
        </div>
      </div>

      <div className="twoColumn lower">
        <div className="panel">
          <div className="panelHeader">
            <div>
              <h2>Eval Results</h2>
              <p>{failed.length ? `${failed.length} failed metric(s)` : "All checks passing"}</p>
            </div>
            {failed.length ? <AlertTriangle size={22} /> : <CheckCircle2 size={22} />}
          </div>
          <div className="evalList">
            {detail.evals.map((item) => (
              <div className="evalRow" key={item.id}>
                <div>
                  <strong>{item.metric_name}</strong>
                  <p>{item.explanation}</p>
                </div>
                <span className={`scoreBadge ${item.passed ? "scorePass" : "scoreFail"}`}>
                  {formatScore(item.score)}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="panelHeader">
            <div>
              <h2>Final Answer</h2>
              <p>What the agent returned to the user.</p>
            </div>
          </div>
          <div className="finalOutput">{detail.final_output}</div>
          <h3>Expected Behavior</h3>
          <p className="expected">{detail.expected_behavior}</p>
        </div>
      </div>
    </section>
  );
}

function setEventIdFromEvent(setEventId: (id: string) => void) {
  return (event: TraceEvent) => setEventId(event.id);
}

function RegressionPanel({ regression }: { regression?: Regression }) {
  if (!regression) {
    return null;
  }
  const scoreBad = regression.delta.score < 0;
  const latencyBad = regression.delta.latency_ms > 0;
  return (
    <section className="panel regression">
      <div className="panelHeader">
        <div>
          <h2>Regression Check</h2>
          <p>Latest run compared against the prior baseline for this task.</p>
        </div>
        <GitCompare size={22} />
      </div>
      <div className="regressionGrid">
        <MetricCard
          label="Score Delta"
          value={`${regression.delta.score > 0 ? "+" : ""}${Math.round(regression.delta.score * 100)} pts`}
          icon={scoreBad ? <ArrowDownRight /> : <ArrowUpRight />}
          tone={scoreBad ? "bad" : "good"}
        />
        <MetricCard
          label="Latency Delta"
          value={`${regression.delta.latency_ms > 0 ? "+" : ""}${regression.delta.latency_ms} ms`}
          icon={latencyBad ? <ArrowUpRight /> : <ArrowDownRight />}
          tone={latencyBad ? "bad" : "good"}
        />
        <MetricCard
          label="Cost Delta"
          value={`${regression.delta.cost_usd > 0 ? "+" : ""}${formatCost(regression.delta.cost_usd)}`}
          icon={<CircleDollarSign />}
          tone={regression.delta.cost_usd > 0 ? "bad" : "good"}
        />
      </div>
    </section>
  );
}

function App() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>();
  const [detail, setDetail] = useState<RunDetail>();
  const [regression, setRegression] = useState<Regression>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    fetch(`${API}/runs`)
      .then((response) => response.json())
      .then((data: Run[]) => {
        setRuns(data);
        setSelectedRunId(data[0]?.id);
      })
      .catch(() => setError("API is not reachable. Start the FastAPI server on port 8000."));
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    fetch(`${API}/runs/${selectedRunId}`)
      .then((response) => response.json())
      .then((data: RunDetail) => {
        setDetail(data);
        return fetch(`${API}/regression/${data.task_id}`);
      })
      .then((response) => (response.ok ? response.json() : undefined))
      .then((data?: Regression) => setRegression(data))
      .catch(() => setError("Failed to load selected run."));
  }, [selectedRunId]);

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId),
    [runs, selectedRunId],
  );

  return (
    <main>
      <header className="hero">
        <div>
          <div className="eyebrow">TraceLab</div>
          <h1>Agent evals and observability for production AI systems.</h1>
          <p>
            Inspect tool calls, latency, token cost, groundedness, and regression failures
            before unreliable agents reach users.
          </p>
        </div>
        <div className="heroCard">
          <span>Portfolio Signal</span>
          <strong>AI Systems + Evals + DevTools</strong>
        </div>
      </header>

      {error ? <div className="error">{error}</div> : null}

      <div className="layout">
        <RunsTable
          runs={runs}
          selected={selectedRun?.id}
          onSelect={(run) => setSelectedRunId(run.id)}
        />
        <div className="mainColumn">
          {detail ? <RunDetailView detail={detail} /> : <div className="panel loading">Loading run detail...</div>}
          <RegressionPanel regression={regression} />
        </div>
      </div>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
