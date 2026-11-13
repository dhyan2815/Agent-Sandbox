import { useEffect, useRef, useState } from "react";
import { nextStep, plural, segments } from "../answer";
import { type AnswerBody, type Citation, type Collection, postJson, streamAnswer } from "../api";
import type { Where } from "../App";

export interface Turn {
  id: number;
  question: string;
  steps: string[]; // finished steps; while busy, the next one is shown as "working"
  working?: string | null;
  answer?: AnswerBody;
  error?: string;
}

type Change = (change: (turn: Turn) => Turn) => void;

/** Ask one question and report its progress through `update`. Never throws. */
export async function askQuestion(
  where: Where,
  question: string,
  history: { question: string; answer: string }[],
  update: Change,
): Promise<void> {
  const fail = (error: string) => update((t) => ({ ...t, error, working: null }));
  update((t) => ({ ...t, working: where.kind === "pack" ? "working" : "searching the documents" }));
  try {
    if (where.kind === "pack") {
      const answer = await postJson<AnswerBody>("/ask", { pack: where.id, question });
      update((t) => ({ ...t, answer, working: null }));
      return;
    }
    let answered = false;
    await streamAnswer(`/collections/${where.id}/ask/stream`, { question, history }, (message) => {
      if (message.type === "step") {
        update((t) => ({ ...t, steps: [...t.steps, message.text], working: nextStep(message.text) }));
      } else if (message.type === "answer") {
        answered = true;
        const { type: _type, ...answer } = message;
        update((t) => ({ ...t, answer, working: null }));
      } else if (message.type === "error") {
        answered = true;
        fail(message.detail);
      }
    });
    if (!answered) fail("The connection closed before an answer arrived.");
  } catch (error) {
    fail((error as Error).message);
  }
}

function AnswerText({ body, onCite }: { body: AnswerBody; onCite: (c: Citation) => void }) {
  return (
    <div className={"answer" + (body.refused ? " refused" : "")}>
      {segments(body.answer, body.citations).map((part, i) =>
        part.kind === "cite" ? (
          <button
            key={i}
            className="cite"
            title={part.citation.title}
            onClick={() => onCite(part.citation)}
          >
            {part.citation.number}
          </button>
        ) : part.kind === "bold" ? (
          <strong key={i}>{part.text}</strong>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </div>
  );
}

function BotMessage({ turn, onCite }: { turn: Turn; onCite: (c: Citation) => void }) {
  const body = turn.answer;
  if (turn.error) {
    return (
      <div className="msg bot">
        <p className="error">{turn.error}</p>
      </div>
    );
  }
  if (!body) {
    return (
      <div className="msg bot" aria-live="polite">
        <ul className="steps">
          {turn.steps.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
          {turn.working && <li className="working">{turn.working}</li>}
        </ul>
      </div>
    );
  }
  const reason = body.trace[body.trace.length - 1] ?? "";
  return (
    <div className="msg bot">
      <AnswerText body={body} onCite={onCite} />
      {body.refused && <p className="note">{reason.replace(/^decline: /, "Why: ")}</p>}
      {body.reading && body.reading.length > 0 && (
        <p className="note reading-note">
          Still reading:{" "}
          {body.reading
            .map((r) =>
              r.pages_total
                ? `${r.name} (searched pages 1–${r.pages_done.toLocaleString()} of ${r.pages_total.toLocaleString()})`
                : `${r.name} (not searched yet)`,
            )
            .join("; ")}
          . Ask again when it is done for a complete answer.
        </p>
      )}
      {body.citations.length > 0 && (
        <div className="sources">
          {body.citations.map((c) => (
            <button key={c.number} className="source" onClick={() => onCite(c)}>
              <span className="cite">{c.number}</span>
              <span className="source-title">{c.title}</span>
            </button>
          ))}
        </div>
      )}
      <details className="trace">
        <summary>
          What the agent did ({plural(body.trace.length, "step")},{" "}
          {plural(body.llm_calls, "model call")})
        </summary>
        <ol>
          {body.trace.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ol>
      </details>
    </div>
  );
}

interface Props {
  where: Where;
  collection?: Collection;
  turns: Turn[];
  busy: boolean;
  onAsk: (question: string) => void;
  onNewChat: () => void;
  onCite: (citation: Citation) => void;
  onUpload: () => void;
}

export function ChatView({ where, collection, turns, busy, onAsk, onNewChat, onCite, onUpload }: Props) {
  const [question, setQuestion] = useState("");
  const box = useRef<HTMLTextAreaElement>(null);
  const messages = useRef<HTMLDivElement>(null);
  const empty = where.kind === "collection" && collection !== undefined && !collection.files.length;

  useEffect(() => {
    messages.current?.scrollTo({ top: messages.current.scrollHeight });
  }, [turns]);

  useEffect(() => {
    if (!busy) box.current?.focus();
  }, [busy]);

  // Grow the box with its text, up to a limit.
  useEffect(() => {
    const node = box.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = Math.min(node.scrollHeight + 2, 140) + "px";
  }, [question]);

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();
    const text = question.trim();
    if (text.length < 3 || busy) return;
    setQuestion("");
    onAsk(text);
  };

  return (
    <div className="view" id="chat-view">
      <div id="messages" ref={messages}>
        <div className="thread" id="thread">
          {empty ? (
            <div className="hint">
              <p>This collection has no documents yet.</p>
              <button className="primary" onClick={onUpload}>
                Upload documents
              </button>
            </div>
          ) : (
            <>
              {!turns.length && (
                <p className="hint">
                  Ask anything these documents can answer. If they cannot, the assistant says so
                  instead of guessing.
                </p>
              )}
              {turns.map((turn) => (
                <div key={turn.id} style={{ display: "contents" }}>
                  <div className="msg user">{turn.question}</div>
                  <BotMessage turn={turn} onCite={onCite} />
                </div>
              ))}
            </>
          )}
        </div>
      </div>
      <div id="composer">
        <form id="ask-form" onSubmit={submit}>
          <textarea
            id="question"
            ref={box}
            rows={1}
            placeholder="Ask a question about these documents"
            maxLength={500}
            aria-label="Question"
            required
            disabled={empty || busy}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
          />
          <button className="primary" id="send" disabled={empty || busy}>
            Ask
          </button>
        </form>
        <div className="row">
          <span id="composer-note">
            {where.kind === "pack"
              ? "Demo packs answer each question on its own."
              : "Follow-up questions use the conversation so far."}
          </span>
          <button className="quiet" id="new-chat" type="button" onClick={onNewChat}>
            New chat
          </button>
        </div>
      </div>
    </div>
  );
}
