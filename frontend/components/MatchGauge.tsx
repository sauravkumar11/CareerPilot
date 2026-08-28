"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

interface MatchGaugeProps {
  score: number; // 0-100
  size?: number;
}

function tierFor(score: number): { color: string; label: string } {
  if (score >= 75) return { color: "#3DDC97", label: "high" };
  if (score >= 50) return { color: "#F5A623", label: "medium" };
  return { color: "#FF5C7A", label: "low" };
}

export function MatchGauge({ score, size = 64 }: MatchGaugeProps) {
  const tier = tierFor(score);
  const radius = size / 2 - 5;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Match score ${score} out of 100, ${tier.label}`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#242B3D"
          strokeWidth={4}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={tier.color}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        />
      </svg>
      <span
        className={clsx("absolute font-mono font-medium tabular-nums")}
        style={{ color: tier.color, fontSize: size * 0.28 }}
      >
        {score}
      </span>
    </div>
  );
}
