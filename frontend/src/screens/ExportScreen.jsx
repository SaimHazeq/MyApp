import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Download, FileVideo, FileText, Check } from "lucide-react";
import { AppShell } from "../widgets/AppShell";
import { Button, Card, Badge } from "../widgets/common";
import { EXPORT_PRESETS } from "../utils/constants";
import { generationService } from "../services/generationService";
import { projectService } from "../services/projectService";
import { api } from "../services/api";
import { toast } from "../state/useToastStore";

async function downloadAuthed(path, filename) {
  const res = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ExportScreen() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [preset, setPreset] = useState("mp4_1080p");
  const [burnIn, setBurnIn] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exported, setExported] = useState(false);

  useEffect(() => {
    projectService.get(projectId).then(setProject);
  }, [projectId]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await generationService.exportMovie(projectId, preset, burnIn);
      setExported(true);
      toast.success("Export ready to download.");
    } catch {
      toast.error("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <AppShell title="Export" subtitle={project?.title || "Your movie"}>
      <div className="max-w-2xl space-y-6">
        <Card className="p-6">
          <h3 className="font-display font-semibold mb-4">Choose a format</h3>
          <div className="grid sm:grid-cols-3 gap-3 mb-6">
            {EXPORT_PRESETS.map((p) => (
              <button
                key={p.value}
                onClick={() => { setPreset(p.value); setExported(false); }}
                className={`text-left p-4 rounded-xl border transition-colors ${
                  preset === p.value ? "border-marquee bg-marquee/10" : "border-studio-border hover:border-marquee/40"
                }`}
              >
                <p className="font-medium text-sm flex items-center gap-1.5">
                  {preset === p.value && <Check size={14} className="text-marquee" />} {p.label}
                </p>
                <p className="text-xs text-studio-muted mt-1">{p.hint}</p>
              </button>
            ))}
          </div>

          <label className="flex items-center gap-3 p-3 rounded-xl bg-studio-surface2 cursor-pointer">
            <input
              type="checkbox"
              checked={burnIn}
              onChange={(e) => { setBurnIn(e.target.checked); setExported(false); }}
              className="accent-marquee w-4 h-4"
            />
            <div>
              <p className="text-sm font-medium">Burn subtitles into video</p>
              <p className="text-xs text-studio-muted">Otherwise subtitles ship as a separate .srt file you can toggle on any player.</p>
            </div>
          </label>
        </Card>

        <Card className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="font-medium">{exported ? "Your export is ready" : "Generate this export"}</p>
            <p className="text-sm text-studio-muted">
              {EXPORT_PRESETS.find((p) => p.value === preset)?.label} {burnIn && <Badge tone="info" className="ml-1">Subtitles burned in</Badge>}
            </p>
          </div>
          {!exported ? (
            <Button onClick={handleExport} loading={exporting}>
              <FileVideo size={16} /> Prepare export
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button onClick={() => downloadAuthed(projectService.videoPath(projectId), `${project?.title || "movie"}.mp4`)}>
                <Download size={16} /> Download MP4
              </Button>
              {!burnIn && (
                <Button variant="secondary" onClick={() => downloadAuthed(projectService.subtitlesPath(projectId), `${project?.title || "movie"}.srt`)}>
                  <FileText size={16} /> Download .srt
                </Button>
              )}
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
