import { useQuery } from "@tanstack/react-query";
import { Canvas, type ThreeEvent, useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { api } from "../api";
import type { EngineEvent, Hit } from "../events";

export interface MapPoint {
  id: string;
  file_id: string;
  title: string;
  xyz: [number, number, number];
}

interface MapBody {
  points: MapPoint[];
  files: { id: string; name: string }[];
  explained: number[];
}

// File colours: a categorical palette that holds in light and dark themes.
const PALETTE = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"];
const DENSE = "#4c8dff";
const BM25 = "#ffb020";
const BOTH = "#ffffff";

const lastHits = (events: EngineEvent[], name: string): Hit[] => {
  for (let i = events.length - 1; i >= 0; i--) if (events[i].t === name) return (events[i].hits as Hit[]) ?? [];
  return [];
};

function Cloud({
  points,
  colours,
  sizes,
  onHover,
}: {
  points: MapPoint[];
  colours: Float32Array;
  sizes: Float32Array;
  onHover: (index: number | null) => void;
}) {
  const positions = useMemo(() => {
    const array = new Float32Array(points.length * 3);
    points.forEach((p, i) => array.set(p.xyz, i * 3));
    return array;
  }, [points]);
  return (
    <points
      onPointerMove={(e: ThreeEvent<PointerEvent>) => onHover(e.index ?? null)}
      onPointerOut={() => onHover(null)}
    >
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colours, 3]} />
        <bufferAttribute attach="attributes-size" args={[sizes, 1]} />
      </bufferGeometry>
      <shaderMaterial
        vertexColors
        transparent
        depthWrite={false}
        vertexShader={`attribute float size; varying vec3 vColor;
          void main() { vColor = color; vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * (3.0 / -mv.z); gl_Position = projectionMatrix * mv; }`}
        fragmentShader={`varying vec3 vColor;
          void main() { float d = length(gl_PointCoord - 0.5); if (d > 0.5) discard;
          gl_FragColor = vec4(vColor, 1.0 - smoothstep(0.35, 0.5, d)); }`}
      />
    </points>
  );
}

function Scene(props: {
  points: MapPoint[];
  colours: Float32Array;
  sizes: Float32Array;
  question: [number, number, number] | null;
  links: [number, number, number][];
  still: boolean;
  onHover: (index: number | null) => void;
  onFps: (fps: number) => void;
}) {
  const group = useRef<THREE.Group>(null);
  const frames = useRef({ count: 0, since: performance.now() });
  const drag = useRef<{ x: number; y: number } | null>(null);
  useFrame((_, delta) => {
    if (group.current && !props.still && !drag.current) group.current.rotation.y += delta * 0.08;
    const f = frames.current;
    f.count += 1;
    const now = performance.now();
    if (now - f.since > 1000) {
      props.onFps(Math.round((f.count * 1000) / (now - f.since)));
      f.count = 0;
      f.since = now;
    }
  });
  const lines = useMemo(() => {
    if (!props.question) return null;
    const array = new Float32Array(props.links.length * 6);
    props.links.forEach((end, i) => array.set([...props.question!, ...end], i * 6));
    return array;
  }, [props.question, props.links]);
  return (
    <group
      ref={group}
      onPointerDown={(e) => (drag.current = { x: e.clientX, y: e.clientY })}
      onPointerUp={() => (drag.current = null)}
      onPointerMove={(e) => {
        if (!drag.current || !group.current) return;
        group.current.rotation.y += (e.clientX - drag.current.x) * 0.005;
        group.current.rotation.x += (e.clientY - drag.current.y) * 0.005;
        drag.current = { x: e.clientX, y: e.clientY };
      }}
    >
      <Cloud points={props.points} colours={props.colours} sizes={props.sizes} onHover={props.onHover} />
      {props.question && (
        <mesh position={props.question}>
          <sphereGeometry args={[0.03, 16, 16]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
      )}
      {lines && (
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[lines, 3]} />
          </bufferGeometry>
          <lineBasicMaterial color="#9ae6b4" transparent opacity={0.8} />
        </lineSegments>
      )}
    </group>
  );
}

/**
 * Knowledge Galaxy: every passage of the collection as a star (PCA to 3D), coloured by file.
 * The latest question is the white comet; its dense hits glow blue, its BM25 hits amber,
 * passages both found white, and lines join it to the reranker's top 5. The list beside
 * the canvas gives their real scores: distances in a projection are only a sketch.
 */
export function Galaxy({ slug, events }: { slug: string; events: EngineEvent[] }) {
  const map = useQuery({ queryKey: ["map", slug], queryFn: () => api<MapBody>(`/collections/${slug}/map`) });
  const [hover, setHover] = useState<number | null>(null);
  const [fps, setFps] = useState(0);
  const still = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const data = map.data;

  const dense = new Map(lastHits(events, "r.dense").map((h) => [h.id, h]));
  const bm25 = new Map(lastHits(events, "r.bm25").map((h) => [h.id, h]));
  const rerank = lastHits(events, "r.rerank");
  const positionEvent = [...events].reverse().find((e) => e.t === "q.position");
  const question = (positionEvent?.xyz as [number, number, number] | undefined) ?? null;

  const { colours, sizes, index } = useMemo(() => {
    const points = data?.points ?? [];
    const fileIndex = new Map((data?.files ?? []).map((f, i) => [f.id, i]));
    const colours = new Float32Array(points.length * 3);
    const sizes = new Float32Array(points.length);
    const colour = new THREE.Color();
    const index = new Map<string, number>();
    points.forEach((p, i) => {
      index.set(p.id, i);
      const inDense = dense.has(p.id);
      const inBm25 = bm25.has(p.id);
      colour.set(
        inDense && inBm25 ? BOTH : inDense ? DENSE : inBm25 ? BM25 : PALETTE[(fileIndex.get(p.file_id) ?? 0) % PALETTE.length],
      );
      if (!inDense && !inBm25 && events.length) colour.multiplyScalar(0.45); // the rest recedes
      colours.set([colour.r, colour.g, colour.b], i * 3);
      sizes[i] = inDense || inBm25 ? 9 : 5;
    });
    return { colours, sizes, index };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, events]);

  if (map.isLoading) return <p className="note">Placing the passages…</p>;
  if (map.error) return <p className="error">{(map.error as Error).message}</p>;
  if (!data) return null;
  const links = rerank
    .map((h) => index.get(h.id))
    .filter((i): i is number => i !== undefined)
    .map((i) => data.points[i].xyz);
  const hovered = hover !== null ? data.points[hover] : null;

  return (
    <div className="galaxy" data-testid="galaxy" data-points={data.points.length} data-fps={fps}>
      <div className="galaxy-canvas">
        <Canvas camera={{ position: [0, 0, 2.6], fov: 50 }} dpr={[1, 2]} raycaster={{ params: { Points: { threshold: 0.02 } } as never }}>
          <color attach="background" args={["#0b0d12"]} />
          <Scene
            points={data.points}
            colours={colours}
            sizes={sizes}
            question={question}
            links={links}
            still={Boolean(still)}
            onHover={setHover}
            onFps={setFps}
          />
        </Canvas>
        <div className="galaxy-hud">
          <span>{data.points.length.toLocaleString()} passages · {fps} fps</span>
          {data.explained.length > 0 && (
            <span>
              axes keep {Math.round(100 * data.explained.reduce((a, b) => a + b, 0))}% of the variance
            </span>
          )}
          {hovered && <span className="hovered">{hovered.title}</span>}
        </div>
      </div>
      <aside className="galaxy-side">
        <p className="legend">
          <span><i style={{ background: DENSE }} /> dense hit</span>
          <span><i style={{ background: BM25 }} /> BM25 hit</span>
          <span><i style={{ background: BOTH }} /> both</span>
          <span><i style={{ background: "#9ae6b4" }} /> line: reranked top 5</span>
        </p>
        {rerank.length > 0 ? (
          <ol className="top5">
            {rerank.map((hit) => (
              <li key={hit.id}>
                <span>{data.points[index.get(hit.id) ?? -1]?.title ?? hit.id}</span>
                <small>
                  rerank {hit.score.toFixed(2)}
                  {dense.has(hit.id) ? ` · cosine ${dense.get(hit.id)!.score.toFixed(3)}` : ""}
                  {bm25.has(hit.id) ? ` · BM25 ${bm25.get(hit.id)!.score.toFixed(2)}` : ""}
                </small>
              </li>
            ))}
          </ol>
        ) : (
          <p className="note">Ask a question in Chat to see where it lands.</p>
        )}
        <p className="note">
          Positions are a 3D projection (PCA) of {data.points.length.toLocaleString()} embeddings; near in
          the picture is not always near in meaning. The scores above are the real ones.
        </p>
        <div className="galaxy-files">
          {data.files.map((f, i) => (
            <span key={f.id}>
              <i style={{ background: PALETTE[i % PALETTE.length] }} /> {f.name}
            </span>
          ))}
        </div>
      </aside>
    </div>
  );
}
