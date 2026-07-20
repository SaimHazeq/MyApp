import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Ban, CheckCircle2, Clapperboard, AlertTriangle } from "lucide-react";
import { AppShell } from "../widgets/AppShell";
import { Button, Card, ProgressBar } from "../widgets/common";
import { FilmRailStepper } from "../widgets/FilmRailStepper";
import { PIPELINE_STAGES } from "../utils/constants";
import { generationService } from "../services/generationService";
import { ConfirmModal } from "../widgets/Modal";
import { toast } from "../state/useToastStore";

export default function GenerationProgressScreen() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const stopPolling = useRef(null);

  useEffect(() => {
    stopPolling.current = generationService.pollUntilDone(projectId, (data, err) => {
      if (err) return;
      setStatus(data);
      if (data.status === "completed") {
        toast.success("Your movie is ready!");
        setTimeout(() => navigate(`/preview/${projectId}`), 800);
      }
    });
    return () => stopPolling.current?.();
  }, [projectId]);

  const currentIndex = status
    ? PIPELINE_STAGES.findIndex((s) => s.key === status.current_stage)
    : 0;

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await generationService.cancel(projectId);
      toast.info("Generation cancelled.");
      navigate("/movies");
    } catch {
      toast.error("Couldn't cancel generation.");
    } finally {
      setCancelling(false);
      setCancelOpen(false);
    }
  };

  const failed = status?.status === "failed";

  return (
    <AppShell title="Generating your movie" subtitle="AI pipeline in progress">
      <div className="max-w-2xl mx-auto">
        <Card className="p-8 sm:p-10">
          {!failed ? (
            <>
              <div className="flex items-center gap-4 mb-8">
                <div className="w-14 h-14 rounded-2xl bg-marquee/15 flex items-center justify-center shrink-0">
                  <Clapperboard className="text-marquee animate-sprocketPulse" size={26} />
                </div>
                <div>
                  <p className="label-eyebrow mb-1">Stage {Math.max(1, currentIndex)} of {PIPELINE_STAGES.length - 1}</p>
                  <h2 className="font-display text-xl font-bold">
                    {status?.current_stage_label || "Queuing your project…"}
                  </h2>
                </div>
              </div>

              <ProgressBar percent={status?.progress_percent || 0} tone="reel" />
              <p className="text-right text-sm text-studio-muted mt-2 mb-8">{status?.progress_percent || 0}%</p>

              <div className="flex justify-center mb-8">
                <FilmRailStepper stages={PIPELINE_STAGES} currentIndex={Math.max(0, currentIndex)} orientation="horizontal" />
              </div>

              <ol className="space-y-2 mb-8">
                {PIPELINE_STAGES.filter((s) => s.key !== "queued").map((s, i) => {
                  const idx = i + 1; // offset since "queued" filtered out but currentIndex counts it
                  const done = currentIndex > idx;
                  const active = currentIndex === idx;
                  return (
                    <li key={s.key} className={`flex items-center gap-3 text-sm ${done ? "text-studio-muted" : active ? "text-studio-text font-medium" : "text-studio-muted/50"}`}>
                      {done ? <CheckCircle2 size={16} className="text-success" /> : <span className={`w-4 h-4 rounded-full border ${active ? "border-reel bg-reel/20" : "border-studio-border"}`} />}
                      {s.label}
                    </li>
                  );
                })}
              </ol>

              <div className="flex justify-center">
                <Button variant="secondary" onClick={() => setCancelOpen(true)}>
                  <Ban size={16} /> Cancel generation
                </Button>
              </div>
            </>
          ) : (
            <div className="text-center py-6">
              <div className="w-14 h-14 rounded-2xl bg-danger/15 flex items-center justify-center mx-auto mb-5">
                <AlertTriangle className="text-danger" size={26} />
              </div>
              <h2 className="font-display text-xl font-bold mb-2">Generation failed</h2>
              <p className="text-studio-muted text-sm mb-6">{status?.error_message || "Something went wrong during generation."}</p>
              <div className="flex justify-center gap-3">
                <Button variant="secondary" onClick={() => navigate(`/create/${projectId}`)}>Edit & retry</Button>
                <Button variant="secondary" onClick={() => navigate("/movies")}>Back to My Movies</Button>
              </div>
            </div>
          )}
        </Card>
      </div>

      <ConfirmModal
        open={cancelOpen}
        title="Cancel generation?"
        description="This will stop the pipeline for this movie. You can restart generation any time from My Movies."
        confirmLabel="Yes, cancel"
        danger
        loading={cancelling}
        onConfirm={handleCancel}
        onClose={() => setCancelOpen(false)}
      />
    </AppShell>
  );
}
