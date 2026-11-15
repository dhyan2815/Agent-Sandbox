import { useEffect, useState } from "react";

/** Shown while the server cannot be reached: a free host that slept is starting again. */
export function WakingScreen({ since }: { since: number }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setSeconds(Math.floor((Date.now() - since) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [since]);
  return (
    <div className="waking" id="waking" role="status" aria-live="polite">
      <div className="waking-card">
        <div className="waking-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <h2>Waking up the server</h2>
        <p>
          This app runs on a free host that sleeps when nobody uses it. Starting again takes up to a
          minute. Your documents are kept and will be here when it is ready.
        </p>
        <p className="note">
          {seconds < 5 ? "Trying to reach it…" : `Waiting for ${seconds} s. This page retries by itself.`}
        </p>
      </div>
    </div>
  );
}
