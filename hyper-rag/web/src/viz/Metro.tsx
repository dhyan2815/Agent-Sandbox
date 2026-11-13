import { useLayoutEffect } from "react";
import { type EngineEvent, metro, type Station } from "../events";
import { markPainted } from "./latency";

interface Props {
  events: EngineEvent[];
  finished: boolean;
  replaying: boolean;
  onStation: (key: string) => void;
}

/** The pipeline strip: always visible above the chat, live while a question runs. */
export function Metro({ events, finished, replaying, onStation }: Props) {
  const stations = metro(events, finished);
  useLayoutEffect(() => markPainted(events.length), [events.length]);
  return (
    <nav className="metro" aria-label="Pipeline of the last question" data-testid="metro">
      <ol>
        {stations.map((station: Station, i) => (
          <li key={station.key} className={`station ${station.state}`}>
            {i > 0 && <span className="rail" aria-hidden="true" />}
            <button
              type="button"
              onClick={() => onStation(station.key)}
              disabled={station.state === "idle" || station.state === "skipped"}
              data-station={station.key}
              data-ms={station.ms}
              aria-label={`${station.label}: ${station.state}${station.ms ? `, ${station.ms} ms` : ""}${station.value ? `, ${station.value}` : ""}`}
            >
              <span className="dot" aria-hidden="true" />
              <span className="name">{station.label}</span>
              <span className="value">
                {station.value || (station.ms ? `${station.ms} ms` : station.state === "skipped" ? "–" : "")}
                {station.value && station.ms ? ` · ${station.ms} ms` : ""}
              </span>
            </button>
          </li>
        ))}
      </ol>
      {replaying && <span className="replaying">replay</span>}
    </nav>
  );
}
