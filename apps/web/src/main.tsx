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
  RefreshCw,
  SlidersHorizontal,
  TrendingUp,
  Wrench,
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

type Task = {
  id: string;
  name: string;
  input: string;
  expected_behavior: string;
  eval_config: {
    required_tools?: string[];
    expected_facts?: string[];
    max_latency_ms?: number;
    max_cost_usd?: number;
    required_citations?: number;
  };
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

function ScoreTrend({ runs }: { runs: Run[] }) {
  if (runs.length < 2) return null;
  const W = 180, H = 34, PAD = 4;
  const scores = runs.map((r) => r.average_score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 0.01;
  const pts = scores
    .map((s, i) => {
      const x = PAD + (i / (scores.length - 1)) * (W - PAD * 2);
      const y = H - PAD - ((s - min) / range) * (H - PAD * 2);
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={W} height={H} style={{ overflow: "visible" }}>
      <polyline points={pts} fill="none" stroke="#2a7c62" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {scores.map((s, i) => {
        const x = PAD + (i / (scores.length - 1)) * (W - PAD * 2);
        const y = H - PAD - ((s - min) / range) * (H - PAD * 2);
        return <circle key={i} cx={x} cy={y} r="3" fill="#2a7c62" />;
      })}
    </svg>
  );
}

function RunsTable({
  runs,
  selected,
  onSelect,
  onRefresh,
}: {
  runs: Run[];
  selected?: string;
  onSelect: (run: Run) => void;
  onRefresh: () => void;
}) {
  const [filter, setFilter] = useState<"all" | "passed" | "failed">("all");
  const [sortBy, setSortBy] = useState<"default" | "score" | "latency" | "cost">("default");

  const passCount = runs.filter((r) => r.status === "passed").length;
  const failCount = runs.filter((r) => r.status === "failed").length;

  const visible = useMemo(() => {
    let list = filter === "all" ? runs : runs.filter((r) => r.status === filter);
    if (sortBy === "score") list = [...list].sort((a, b) => b.average_score - a.average_score);
    else if (sortBy === "latency") list = [...list].sort((a, b) => a.total_latency_ms - b.total_latency_ms);
    else if (sortBy === "cost") list = [...list].sort((a, b) => a.estimated_cost_usd - b.estimated_cost_usd);
    return list;
  }, [runs, filter, sortBy]);

  return (
    <section className="panel runsPanel">
      <div className="panelHeader">
        <div>
          <h2>Agent Runs</h2>
          <p>
            <span className="countBadge countPass">{passCount} passed</span>{" "}
            <span className="countBadge countFail">{failCount} failed</span>
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <ScoreTrend runs={runs} />
          <button className="iconActionBtn" onClick={onRefresh} title="Refresh">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="filterBar">
        <SlidersHorizontal size={14} style={{ color: "#66706a" }} />
        {(["all", "passed", "failed"] as const).map((f) => (
          <button key={f} className={`filterChip ${filter === f ? "filterChipActive" : ""}`} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
        <select className="sortSelect" value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}>
          <option value="default">Default order</option>
          <option value="score">Sort: Score ↓</option>
          <option value="latency">Sort: Latency ↑</option>
          <option value="cost">Sort: Cost ↑</option>
        </select>
        <TrendingUp size={14} style={{ color: "#66706a", marginLeft: "auto" }} />
      </div>

      <div className="runList">
        {visible.length === 0 && (
          <p style={{ padding: "16px", color: "#66706a", fontSize: "13px" }}>No runs match the filter.</p>
        )}
        {visible.map((run) => (
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

function TasksView() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    fetch(`${API}/tasks`)
      .then((r) => r.json())
      .then(setTasks)
      .catch(() => {});
  }, []);

  return (
    <div className="tasksGrid">
      {tasks.map((task) => (
        <div className="taskCard panel" key={task.id}>
          <div className="taskCardHeader">
            <div className="eyebrow">{task.id}</div>
            <h3>{task.name}</h3>
          </div>
          <p className="taskInput">{task.input}</p>
          <p className="taskExpected">{task.expected_behavior}</p>
          <div className="taskCriteria">
            {task.eval_config.required_tools?.map((tool) => (
              <span className="criteriaTag criteriaTagTool" key={tool}>
                <Wrench size={11} />
                {tool}
              </span>
            ))}
            {task.eval_config.max_latency_ms != null && (
              <span className="criteriaTag">
                <Clock3 size={11} />
                {task.eval_config.max_latency_ms} ms
              </span>
            )}
            {task.eval_config.max_cost_usd != null && (
              <span className="criteriaTag">
                <CircleDollarSign size={11} />${task.eval_config.max_cost_usd}
              </span>
            )}
            {task.eval_config.required_citations != null &&
              task.eval_config.required_citations > 0 && (
                <span className="criteriaTag">
                  {task.eval_config.required_citations} citations
                </span>
              )}
          </div>
        </div>
      ))}
    </div>
  );
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
  const [tab, setTab] = useState<"runs" | "tasks">("runs");
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>();
  const [detail, setDetail] = useState<RunDetail>();
  const [regression, setRegression] = useState<Regression>();
  const [error, setError] = useState<string>();
  const [refreshKey, setRefreshKey] = useState(0);

  function loadRuns() {
    fetch(`${API}/runs`)
      .then((response) => response.json())
      .then((data: Run[]) => {
        setRuns(data);
        setSelectedRunId((prev) => prev ?? data[0]?.id);
      })
      .catch(() => setError("API is not reachable. Start the FastAPI server on port 8000."));
  }

  useEffect(() => { loadRuns(); }, [refreshKey]);

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

      <nav className="tabNav">
        <button
          className={`tabBtn ${tab === "runs" ? "tabBtnActive" : ""}`}
          onClick={() => setTab("runs")}
        >
          <PlayCircle size={16} />
          Runs
        </button>
        <button
          className={`tabBtn ${tab === "tasks" ? "tabBtnActive" : ""}`}
          onClick={() => setTab("tasks")}
        >
          <ListChecks size={16} />
          Tasks
        </button>
      </nav>

      {tab === "runs" ? (
        <div className="layout">
          <RunsTable
            runs={runs}
            selected={selectedRun?.id}
            onSelect={(run) => setSelectedRunId(run.id)}
            onRefresh={() => setRefreshKey((k) => k + 1)}
          />
          <div className="mainColumn">
            {detail ? <RunDetailView detail={detail} /> : <div className="panel loading">Loading run detail...</div>}
            <RegressionPanel regression={regression} />
          </div>
        </div>
      ) : (
        <div className="tasksContainer">
          <TasksView />
        </div>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
