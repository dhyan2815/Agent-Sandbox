// Event-to-screen latency, the phase 3 acceptance number: the time from an event arriving
// on the stream to the frame that shows it. Kept on window for the end-to-end script.

declare global {
  interface Window {
    __hrLatency?: number[];
  }
}

let arrived: number | null = null;

export function markArrived(): void {
  arrived = performance.now();
}

export function markPainted(_eventCount: number): void {
  if (arrived === null) return;
  const started = arrived;
  arrived = null;
  requestAnimationFrame(() => {
    (window.__hrLatency ??= []).push(performance.now() - started);
  });
}
