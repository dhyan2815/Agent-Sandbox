import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { plural } from "./answer";
import { type AnswerBody, type Citation, type Collection, type Config, type Source, api } from "./api";
import { ChatView, type Turn, askQuestion } from "./components/ChatView";
import { EvalView } from "./components/EvalView";
import { FilesView } from "./components/FilesView";
import { Sidebar } from "./components/Sidebar";
import { SourcePanel, type SourceView } from "./components/SourcePanel";

export type Where = { kind: "collection" | "pack"; id: string };
export type Tab = "chat" | "files" | "eval";

const keyOf = (where: Where) => `${where.kind}:${where.id}`;

export function App() {
  const client = useQueryClient();
  const config = useQuery({ queryKey: ["config"], queryFn: () => api<Config>("/config") });
  const packs = useQuery({
    queryKey: ["packs"],
    queryFn: async () => (await api<{ packs: string[] }>("/packs")).packs,
  });
  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: async () => (await api<{ collections: Collection[] }>("/collections")).collections,
  });
  const refreshCollections = useCallback(
    () => client.invalidateQueries({ queryKey: ["collections"] }),
    [client],
  );

  const [where, setWhere] = useState<Where | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [chats, setChats] = useState<Record<string, Turn[]>>({});
  const [busy, setBusy] = useState(false);
  const [source, setSource] = useState<SourceView | null>(null);

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
      setChats((all) => ({ ...all, [key]: [...(all[key] ?? []), { id, question, steps: [] }] }));
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

  return (
    <div className={"app" + (source ? " with-source" : "")} id="app">
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
              {(["chat", "files", "eval"] as Tab[])
                .filter((name) => isCollection || name === "chat")
                .map((name) => (
                  <button
                    key={name}
                    role="tab"
                    aria-selected={tab === name}
                    className={"tab" + (tab === name ? " active" : "")}
                    data-tab={name}
                    onClick={() => setTab(name)}
                  >
                    {{ chat: "Chat", files: "Files", eval: "Evaluation" }[name]}
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
          />
        )}
        {collection && tab === "files" && cfg && (
          <FilesView collection={collection} config={cfg} onChanged={refreshCollections} />
        )}
        {collection && tab === "eval" && cfg && <EvalView slug={collection.slug} config={cfg} />}
      </main>

      {source && <SourcePanel view={source} onClose={() => setSource(null)} />}
    </div>
  );
}
