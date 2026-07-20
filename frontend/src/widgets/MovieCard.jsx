import { Link } from "react-router-dom";
import { Clock, Play, Loader2, AlertTriangle } from "lucide-react";
import { Badge } from "./common";
import { formatDate } from "../utils/validators";

const STATUS_META = {
  draft: { tone: "neutral", label: "Draft" },
  completed: { tone: "success", label: "Ready" },
  failed: { tone: "danger", label: "Failed" },
};

function statusMeta(status) {
  if (STATUS_META[status]) return STATUS_META[status];
  return { tone: "info", label: "Generating…" };
}

export function MovieCard({ project }) {
  const meta = statusMeta(project.status);
  const isGenerating = !["draft", "completed", "failed"].includes(project.status);
  const linkTo = project.status === "completed" ? `/preview/${project.id}`
    : isGenerating ? `/generating/${project.id}`
    : `/create/${project.id}`;

  return (
    <Link to={linkTo} className="card group overflow-hidden flex flex-col hover:border-marquee/50 transition-colors">
      <div className="relative aspect-video bg-studio-surface2 flex items-center justify-center overflow-hidden">
        {project.thumbnail_path ? (
          <div className="w-full h-full bg-gradient-to-br from-studio-surface2 to-studio-bg flex items-center justify-center">
            <Play className="text-marquee/70" size={32} />
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-studio-muted">
            {isGenerating ? <Loader2 className="animate-spin" size={28} /> : <Play size={28} />}
          </div>
        )}
        <div className="absolute top-2 right-2">
          <Badge tone={meta.tone}>{meta.label}</Badge>
        </div>
      </div>
      <div className="p-4 space-y-2">
        <h3 className="font-display font-semibold truncate group-hover:text-marquee transition-colors">
          {project.title || "Untitled movie"}
        </h3>
        <div className="flex items-center justify-between text-xs text-studio-muted">
          <span className="flex items-center gap-1">
            <Clock size={13} /> {project.duration_minutes} min
          </span>
          <span>{formatDate(project.updated_at)}</span>
        </div>
        {isGenerating && (
          <div className="flex items-center gap-1.5 text-xs text-reel">
            <Loader2 size={12} className="animate-spin" /> {project.progress_percent}% complete
          </div>
        )}
        {project.status === "failed" && (
          <div className="flex items-center gap-1.5 text-xs text-danger">
            <AlertTriangle size={12} /> Generation failed
          </div>
        )}
      </div>
    </Link>
  );
}
