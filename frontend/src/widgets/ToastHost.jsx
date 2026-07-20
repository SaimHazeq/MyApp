import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { useToastStore } from "../state/useToastStore";

const ICONS = { success: CheckCircle2, error: AlertCircle, info: Info };
const TONES = {
  success: "border-success/40 text-success",
  error: "border-danger/40 text-danger",
  info: "border-reel/40 text-reel",
};

export function ToastHost() {
  const { toasts, dismiss } = useToastStore();

  if (!toasts.length) return null;

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80">
      {toasts.map((t) => {
        const Icon = ICONS[t.type] || Info;
        return (
          <div
            key={t.id}
            className={`card flex items-start gap-2.5 px-4 py-3 border ${TONES[t.type] || TONES.info} animate-[fadeIn_0.2s_ease-out]`}
          >
            <Icon size={18} className="shrink-0 mt-0.5" />
            <p className="text-sm text-studio-text flex-1">{t.message}</p>
            <button onClick={() => dismiss(t.id)} className="text-studio-muted hover:text-studio-text">
              <X size={16} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
