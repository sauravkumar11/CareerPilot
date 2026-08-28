"use client";

import clsx from "clsx";

export function SkillTagList({
  skills,
  variant = "neutral",
}: {
  skills: string[];
  variant?: "neutral" | "high" | "low";
}) {
  if (skills.length === 0) return null;

  const colorClass = {
    neutral: "border-border text-text-secondary",
    high: "border-high/40 text-high",
    low: "border-low/40 text-low",
  }[variant];

  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <span
          key={skill}
          className={clsx("rounded-full border px-2.5 py-1 font-mono text-xs", colorClass)}
        >
          {skill}
        </span>
      ))}
    </div>
  );
}
