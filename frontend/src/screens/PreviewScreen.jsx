import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Download, Share2, Captions, Clock } from "lucide-react";
import { AppShell } from "../widgets/AppShell";
import { Button, Card, Badge, Spinner } from "../widgets/common";
import { useAuthedBlobUrl } from "../utils/useAuthedBlobUrl";
import { projectService } from "../services/projectService";
import { formatDuration } from "../utils/validators";

export default function PreviewScreen() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [subtitlesOn, setSubtitlesOn] = useState(true);

  useEffect(() => {
    projectService.get(projectId).then(setProject);
  }, [projectId]);

  const { url: videoUrl, loading: videoLoading } = useAuthedBlobUrl(project ? projectService.videoPath(projectId) : null);
  const { url: subsUrl } = useAuthedBlobUrl(project?.subtitle_path ? projectService.subtitlesPath(projectId) : null);

  return (
    <AppShell
      title={project?.title || "Preview"}
      subtitle="Your movie"
      actions={
        <Button onClick={() => navigate(`/export/${projectId}`)}>
          <Download size={16} /> Export
        </Button>
      }
    >
      <div className="grid lg:grid-cols-[1fr_320px] gap-6">
        <Card className="overflow-hidden">
          <div className="aspect-video bg-black flex items-center justify-center">
            {videoLoading ? (
              <Spinner size={32} />
            ) : videoUrl ? (
              <video key={videoUrl} controls autoPlay className="w-full h-full" crossOrigin="anonymous">
                <source src={videoUrl} type="video/mp4" />
                {subtitlesOn && subsUrl && <track kind="subtitles" src={subsUrl} srcLang="en" label="English" default />}
              </video>
            ) : (
              <p className="text-studio-muted text-sm">Video not available.</p>
            )}
          </div>
          <div className="p-5 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <Badge tone="success">Ready</Badge>
              <span className="text-sm text-studio-muted flex items-center gap-1">
                <Clock size={13} /> {project ? formatDuration(project.duration_minutes) : "--:--"}
              </span>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setSubtitlesOn((s) => !s)}>
                <Captions size={16} /> {subtitlesOn ? "Subtitles on" : "Subtitles off"}
              </Button>
              <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(window.location.href)}>
                <Share2 size={16} /> Copy link
              </Button>
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="font-display font-semibold mb-4">Scenes</h3>
          <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
            {project?.scenes?.length ? (
              project.scenes.map((scene) => (
                <div key={scene.id} className="border border-studio-border rounded-xl p-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-mono text-marquee">Scene {scene.index + 1}</span>
                    <span className="text-xs text-studio-muted">{scene.duration_seconds}s</span>
                  </div>
                  <p className="text-sm text-studio-text/90 line-clamp-2">{scene.text}</p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    <Badge tone="neutral">{scene.location}</Badge>
                    <Badge tone="info">{scene.emotion}</Badge>
                    {scene.sfx_tags?.map((tag) => <Badge key={tag} tone="warning">{tag}</Badge>)}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-studio-muted">No scene breakdown available.</p>
            )}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
