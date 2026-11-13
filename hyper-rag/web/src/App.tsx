import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { plural } from "./answer";
import { type AnswerBody, type Citation, type Collection, type Config, type Source, api, isReading } from "./api";
import { ChatView, type Turn, askQuestion } from "./components/ChatView";
import { CheckView } from "./components/CheckView";
import { EvalView } from "./components/EvalView";
import { FilesView } from "./components/FilesView";
import { Sidebar } from "./components/Sidebar";
import { Inspector, type InspectorTab, type SourceView } from "./components/SourcePanel";
import { type EngineEvent, quota } from "./events";
import { lazy, Suspense } from "react";
import { WakingScreen } from "./components/WakingScreen";
import { useServerStatus } from "./status";
import { Metro } from "./viz/Metro";
import { Metrics } from "./viz/Metrics";

// three.js is large: the Galaxy is loaded only when the Explore tab is opened.
const Galaxy = lazy(() => import("./viz/Galaxy").then((m) => ({ default: m.Galaxy })));
import { RankRace } from "./viz/RankRace";

export type Where = { kind: "collection" | "pack"; id: string };
export type Tab = "chat" | "files" | "check" | "eval" | "explore";

const keyOf = (where: Where) => `${where.kind}:${where.id}`;

export function App() {
  const client = useQueryClient();
  const server = useServerStatus();
  const config = useQuery({ queryKey: ["config"], queryFn: () => api<Config>("/config") });
  const packs = useQuery({
    queryKey: ["packs"],
    queryFn: async () => (await api<{ packs: string[] }>("/packs")).packs,
  });
  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: async () => (await api<{ collections: Collection[] }>("/collections")).collections,
    // While any file is being read, keep the list (and its progress) fresh.
    refetchInterval: (query) =>
      query.state.data?.some((c) => c.files.some(isReading)) ? 1500 : false,
  });
  const refreshCollections = useCallback(
    () => client.invalidateQueries({ queryKey: ["collections"] }),
    [client],
  );

  const [where, setWhere] = useState<Where | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [chats, setChats] = useState<Record<string, Turn[]>>({});
  const [busy, setBusy] = useState(false);
  const [source, setSourceView] = useState<SourceView | null>(null);
  const [inspector, setInspector] = useState<{ tab: InspectorTab; turnId: number | null } | null>(null);
  const [replay, setReplay] = useState<{ events: EngineEvent[]; done: boolean } | null>(null);
  const replayTimer = useRef<number[]>([]);
  const setSource = useCallback((view: SourceView | null) => {
    setSourceView(view);
    setInspector(view ? { tab: "source", turnId: null } : null);
  }, []);

  const list = collections.data ?? [];
  const collection = where?.kind === "collection" ? list.find((c) => c.slug === where.id) : undefined;

  const select = useCallback(
    (next: Where, nextTab?: Tab) => {
      const target = next.kind === "collection" ? list.find((c) => c.slug === next.id) : undefined;
      setWhere(next);
      // A new, empty collection opens on Files: there is nothing to ask yet.
      setTab(nextTab ?? (target && !target.files.length ? "files" : "chat"));
      setSource(null);
    },
    [list],
  );

  // On first load, open the newest collection.
  const opened = useRef(false);
  useEffect(() => {
    if (opened.current || !collections.data) return;
    opened.current = true;
    const newest = collections.data[collections.data.length - 1];
    if (newest) select({ kind: "collection", id: newest.slug });
  }, [collections.data, select]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === "Escape" && setSource(null);
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, []);

  const updateTurn = useCallback((key: string, id: number, change: (turn: Turn) => Turn) => {
    setChats((all) => ({ ...all, [key]: (all[key] ?? []).map((t) => (t.id === id ? change(t) : t)) }));
  }, []);

  const ask = useCallback(
    async (question: string) => {
      if (!where || busy) return;
      const key = keyOf(where);
      const turns = chats[key] ?? [];
      // Only answered turns are sent as history: a refusal carries nothing to refer back to.
      const history = turns
        .filter((t) => t.answer && !t.answer.refused)
        .slice(-3)
        .map((t) => ({ question: t.question, answer: (t.answer as AnswerBody).answer.slice(0, 4000) }));
      const id = Date.now();
      setChats((all) => ({ ...all, [key]: [...(all[key] ?? []), { id, question, steps: [], events: [] }] }));
      stopReplay();
      setBusy(true);
      await askQuestion(where, question, history, (change) => updateTurn(key, id, change));
      setBusy(false);
    },
    [where, busy, chats, updateTurn],
  );

  const openCitation = useCallback(
    async (citation: Citation) => {
      if (!where) return;
      if (where.kind === "pack") {
        // Demo packs cite public web pages or repository files; only http(s) links are opened.
        if (/^https?:\/\//.test(citation.url)) window.open(citation.url, "_blank", "noopener");
        const lines = citation.text.split("\n").map((text) => [{ text, hit: true }]);
        setSource({ title: citation.title, subtitle: "Demo pack passage", lines, source: null });
        return;
      }
      try {
        const found = await api<Source>(
          `/collections/${where.id}/source?chunk_id=${encodeURIComponent(citation.chunk_id)}`,
        );
        setSource({
          title: found.file_name,
          subtitle: found.unit_label || "Whole file",
          lines: found.lines,
          source: found,
        });
      } catch (error) {
        setSource({ title: citation.title, subtitle: (error as Error).message, lines: [], source: null });
      }
    },
    [where],
  );

  // --- the visualizer: the strip follows the latest answer, or a replay of an earlier one

  const turns = where ? (chats[keyOf(where)] ?? []) : [];
  const latest = turns[turns.length - 1];
  const stopReplay = () => {
    replayTimer.current.forEach(clearTimeout);
    replayTimer.current = [];
    setReplay(null);
  };
  const startReplay = (turn: Turn) => {
    stopReplay();
    // The saved run is the source of truth; the events held in the tab are the same ones.
    const play = (events: EngineEvent[]) => {
      const total = events.reduce((sum, e) => sum + (typeof e.ms === "number" ? e.ms : 0), 0);
      const scale = total > 0 ? Math.min(1, 3000 / total) : 1; // a replay takes at most 3 s
      let at = 0;
      setReplay({ events: [], done: false });
      events.forEach((event, i) => {
        at += (typeof event.ms === "number" ? event.ms : 0) * scale + 40;
        replayTimer.current.push(
          window.setTimeout(
            () => setReplay({ events: events.slice(0, i + 1), done: i === events.length - 1 }),
            at,
          ),
        );
      });
    };
    const runId = turn.answer?.run_id;
    if (runId && where?.kind === "collection") {
      api<{ events: EngineEvent[] }>(`/collections/${where.id}/runs/${runId}`)
        .then((run) => play(run.events))
        .catch(() => play(turn.events));
    } else play(turn.events);
  };
  const stripEvents = replay ? replay.events : (latest?.events ?? []);
  const stripFinished = replay ? replay.done : Boolean(latest?.answer || latest?.error || !latest);
  const inspectedTurn = turns.find((t) => t.id === inspector?.turnId) ?? latest;
  const fileNames = new Map((collection?.files ?? []).map((f) => [f.id, f]));
  const label = (chunkId: string) => {
    const match = chunkId.match(/^([0-9a-f]{12})\/(\d+)#([sc]?)(\d+)$/);
    const file = match && fileNames.get(match[1]);
    if (!file || !match) return chunkId;
    const unit = file.kind === "pdf" ? `p.${match[2]}` : `§${match[2]}`;
    if (match[3] === "c") return `${file.name}: chapter ${Number(match[4]) + 1} summary`;
    if (match[3] === "s") return `${file.name} ${unit}: section summary`;
    return `${file.name} ${unit}${match[4] !== "0" ? ` (${Number(match[4]) + 1})` : ""}`;
  };
  const openChunk = (chunkId: string) =>
    openCitation({ number: 0, title: label(chunkId), url: "", chunk_id: chunkId, doc_id: "", text: "" });
  const budget = quota(turns.flatMap((t) => t.events));

  const removeCollection = async () => {
    if (!collection) return;
    const message = `Delete "${collection.name}" and its ${plural(collection.files.length, "uploaded file")}? This cannot be undone.`;
    if (!confirm(message)) return;
    await api(`/collections/${collection.slug}`, { method: "DELETE" });
    setChats(({ [keyOf(where!)]: _gone, ...rest }) => rest);
    setWhere(null);
    setSource(null);
    await refreshCollections();
  };

  const cfg = config.data;
  const failed = config.error ?? collections.error;
  const isCollection = where?.kind === "collection";
  const chunks = collection?.files.reduce((sum, f) => sum + f.chunks, 0) ?? 0;

  if (server.status === "down") return <WakingScreen since={server.since} />;

  return (
    <div className={"app" + (inspector ? " with-source" : "")} id="app">
      <Sidebar
        config={cfg}
        collections={list}
        packs={packs.data ?? []}
        where={where}
        onSelect={select}
        onCreated={async (slug) => {
          await refreshCollections();
          setWhere({ kind: "collection", id: slug });
          setTab("files");
          setSource(null);
        }}
      />

      <main>
        {server.status === "warming" && (
          <div className="banner" id="warming-banner" role="status">
            Loading the search models. The first question may take a little longer.
          </div>
        )}
        {cfg?.offline && (
          <div className="banner" id="offline-banner">
            Offline demo mode: answers come from a rule-based stand-in, not a language model.
            Start the server without HYPER_RAG_OFFLINE to use the real one.
          </div>
        )}

        {!where && (
          <div className="view" id="welcome">
            <div className="welcome">
              {failed ? (
                <p className="error">Could not reach the server: {(failed as Error).message}</p>
              ) : (
                <>
                  <h2>Ask questions about your own documents</h2>
                  <p>
                    Create a collection on the left, drop in PDFs, Word, PowerPoint or Excel files,
                    images or text, and ask. Tables are kept as tables, and text inside images and
                    scans is read by OCR on this machine.
                  </p>
                  <p>
                    Each answer cites its sources. Click a citation to open the page it came from,
                    with the passage highlighted.
                  </p>
                </>
              )}
            </div>
          </div>
        )}

        {where && (
          <header className="top" id="top">
            <div className="top-row">
              <h2 id="title">{isCollection ? (collection?.name ?? where.id) : `${where.id} (demo pack)`}</h2>
              <p id="subtitle">
                {collection
                  ? `${plural(collection.files.length, "file")}, ${chunks} searchable passages`
                  : isCollection
                    ? ""
                    : "A built-in corpus that ships with the project"}
                {budget && typeof budget.requests_left_today === "number" && (
                  <span className="quota" title={`Reported by ${String(budget.model)} with its last reply`}>
                    {" · "}
                    {budget.requests_left_today.toLocaleString()} model requests left today
                  </span>
                )}
              </p>
              {isCollection && (
                <button
                  className="quiet"
                  id="delete-collection"
                  title="Delete this collection and its files"
                  onClick={removeCollection}
                >
                  Delete
                </button>
              )}
            </div>
            <nav className="tabs" id="tabs" role="tablist">
              {(["chat", "files", "check", "eval", "explore"] as Tab[])
                .filter((name) => isCollection || name === "chat")
                .filter((name) => name !== "explore" || cfg?.demo_mode)
                .map((name) => (
                  <button
                    key={name}
                    role="tab"
                    aria-selected={tab === name}
                    className={"tab" + (tab === name ? " active" : "")}
                    data-tab={name}
                    onClick={() => setTab(name)}
                  >
                    {{ chat: "Chat", files: "Files", check: "Check claims", eval: "Evaluation", explore: "Explore" }[name]}
                  </button>
                ))}
            </nav>
          </header>
        )}

        {where && tab === "chat" && (
          <ChatView
            where={where}
            collection={collection}
            turns={chats[keyOf(where)] ?? []}
            busy={busy}
            onAsk={ask}
            onNewChat={() => !busy && setChats((all) => ({ ...all, [keyOf(where)]: [] }))}
            onCite={openCitation}
            onUpload={() => setTab("files")}
            onReplay={startReplay}
            onRetrieval={(turn) => setInspector({ tab: "retrieval", turnId: turn.id })}
            strip={
              isCollection ? (
                <Metro
                  events={stripEvents}
                  finished={stripFinished}
                  replaying={Boolean(replay)}
                  onStation={() => setInspector({ tab: "retrieval", turnId: latest?.id ?? null })}
                />
              ) : null
            }
          />
        )}
        {collection && tab === "files" && cfg && (
          <FilesView collection={collection} config={cfg} onChanged={refreshCollections} />
        )}
        {collection && tab === "check" && <CheckView slug={collection.slug} onCite={openCitation} />}
        {collection && tab === "eval" && cfg && <EvalView slug={collection.slug} config={cfg} />}
        {collection && tab === "explore" && cfg?.demo_mode && (
          <div className="view" id="explore-view">
            <div className="pad wide">
              <Suspense fallback={<p className="note">Loading the 3D view…</p>}>
                <Galaxy slug={collection.slug} events={latest?.events ?? []} />
              </Suspense>
              <Metrics slug={collection.slug} passages={chunks} />
            </div>
          </div>
        )}
      </main>

      {inspector && (
        <Inspector
          tab={inspector.tab}
          source={source}
          retrieval={
            inspectedTurn?.events.length ? (
              <>
                <h3 className="inspector-title">Why these passages</h3>
                <p className="note">{inspectedTurn.question}</p>
                <RankRace
                  events={inspectedTurn.events}
                  label={label}
                  onOpen={where?.kind === "collection" ? openChunk : undefined}
                />
              </>
            ) : null
          }
          onTab={(tab) => setInspector((now) => (now ? { ...now, tab } : now))}
          onClose={() => setSource(null)}
        />
      )}
    </div>
  );
}
