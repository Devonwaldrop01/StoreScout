"use client";

/** Loading skeletons — one shimmer vocabulary so every page signals "working". */

export function Skeleton({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden />;
}

/** A card-shaped skeleton block. */
export function SkeletonCard({ className = "", height = 96 }: { className?: string; height?: number }) {
  return <Skeleton className={className} style={{ height }} />;
}

/** N stat-tile skeletons in a responsive row. */
export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {Array.from({ length: count }).map((_, i) => <Skeleton key={i} style={{ height: 72 }} />)}
    </div>
  );
}

/** Skeleton rows for a loading list/table. */
export function SkeletonRows({ rows = 5, height = 52 }: { rows?: number; height?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} style={{ height }} />)}
    </div>
  );
}
