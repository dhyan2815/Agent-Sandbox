import { useState } from "react";
import { plural } from "../answer";
import { type Collection, type Config, postJson } from "../api";
import type { Where } from "../App";

interface Props {
  config?: Config;
  collections: Collection[];
  packs: string[];
  where: Where | null;
  onSelect: (where: Where) => void;
  onCreated: (slug: string) => void;
}

export function Sidebar({ config, collections, packs, where, onSelect, onCreated }: Props) {
  const [name, setName] = useState("");
  const active = (kind: Where["kind"], id: string) => where?.kind === kind && where.id === id;

  const create = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const created = await postJson<Collection>("/collections", { name });
      setName("");
      onCreated(created.slug);
    } catch (error) {
      alert((error as Error).message);
    }
  };

  const modelLine = !config
    ? "Ask your documents. Every answer cites its page."
    : config.offline
      ? "Offline demo mode"
      : `Answers by ${config.generator}`;

  return (
    <aside className="nav">
      <div className="brand">
        <h1>Hyper-RAG</h1>
        <p id="model-line">{modelLine}</p>
      </div>
      <div className="nav-scroll">
        <h2>Your collections</h2>
        <div id="collection-list">
          {!collections.length && <p className="nav-empty">None yet. Name one below.</p>}
          {collections.map((c) => (
            <button
              key={c.slug}
              className={"nav-item" + (active("collection", c.slug) ? " active" : "")}
              aria-current={active("collection", c.slug) || undefined}
              onClick={() => onSelect({ kind: "collection", id: c.slug })}
            >
              <span>{c.name}</span>
              <small>{plural(c.files.length, "file")}</small>
            </button>
          ))}
        </div>
        <form id="new-collection" onSubmit={create}>
          <input
            id="new-name"
            placeholder="New collection name"
            maxLength={60}
            aria-label="New collection name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <button className="primary" title="Create collection">
            Add
          </button>
        </form>
        <h2>Built-in demo packs</h2>
        <div id="pack-list">
          {packs.map((pack) => (
            <button
              key={pack}
              className={"nav-item" + (active("pack", pack) ? " active" : "")}
              aria-current={active("pack", pack) || undefined}
              onClick={() => onSelect({ kind: "pack", id: pack })}
            >
              <span>{pack}</span>
            </button>
          ))}
        </div>
      </div>
      {config?.login && (
        <form method="post" action="/logout" id="logout" className="logout">
          <button type="submit">Log out</button>
        </form>
      )}
    </aside>
  );
}
