import { type EngineEvent, stages, totals } from "../events";

interface Props {
  events: EngineEvent[];
  onReplay?: () => void;
  onRetrieval?: () => void;
}

/** One bar per stage, like a browser's network tab: where the time and the tokens went. */
export function Waterfall({ events, onReplay, onRetrieval }: Props) {
  const all = stages(events);
  if (!all.length) return null;
  const sum = totals(events);
  const total = Math.max(sum.ms, 1);
  let offset = 0;
  return (
    <details className="waterfall" data-testid="waterfall">
      <summary>
        <span className="mini" aria-hidden="true">
          {all.map((stage, i) => (
            <span key={i} className={`seg ${stage.key}`} style={{ flexGrow: Math.max(stage.ms, total / 200) }} />
          ))}
        </span>
        <span data-total-ms={sum.ms}>
          {formatMs(sum.ms)} · {sum.calls} model call{sum.calls === 1 ? "" : "s"}
          {sum.tokens ? ` · ${sum.tokens.toLocaleString()} tokens` : ""}
        </span>
        {onReplay && (
          <button type="button" className="quiet replay" onClick={(e) => (e.preventDefault(), onReplay())}>
            ↻ replay
          </button>
        )}
        {onRetrieval && (
          <button type="button" className="quiet" onClick={(e) => (e.preventDefault(), onRetrieval())}>
            ranking
          </button>
        )}
      </summary>
      <table className="bars">
        <tbody>
          {all.map((stage, i) => {
            const left = (100 * offset) / total;
            offset += stage.ms;
            return (
              <tr key={i} data-stage={stage.label} data-ms={stage.ms}>
                <th scope="row">{stage.label}</th>
                <td className="track">
                  <span
                    className={`bar-fill ${stage.key}`}
                    style={{ marginLeft: `${left}%`, width: `${Math.max((100 * stage.ms) / total, 0.4)}%` }}
                  />
                </td>
                <td className="num">{formatMs(stage.ms)}</td>
                <td className="detail">
                  {stage.detail}
                  {stage.tokens ? ` · ${stage.tokens.toLocaleString()} tok` : ""}
                  {stage.cached ? " · cached" : ""}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </details>
  );
}

export const formatMs = (ms: number) =>
  ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : ms >= 10 ? `${Math.round(ms)} ms` : `${ms.toFixed(1)} ms`;
