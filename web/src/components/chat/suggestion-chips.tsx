"use client";

const SUGGESTIONS = [
  "What was yesterday's revenue?",
  "Show me top 5 items this week",
  "Revenue heatmap by hour",
  "Which platform is most profitable?",
  "Show customer churn risk",
  "Compare weekday vs weekend revenue",
];

interface SuggestionChipsProps {
  onSelect: (text: string) => void;
}

export function SuggestionChips({ onSelect }: SuggestionChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {SUGGESTIONS.map((text) => (
        <button
          key={text}
          type="button"
          onClick={() => onSelect(text)}
          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700"
        >
          {text}
        </button>
      ))}
    </div>
  );
}
