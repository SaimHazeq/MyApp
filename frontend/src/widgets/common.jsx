import { Loader2 } from "lucide-react";

export function Button({ variant = "primary", loading, className = "", children, disabled, ...props }) {
  const base = variant === "primary" ? "btn-primary" : variant === "danger" ? "btn-danger" : "btn-secondary";
  return (
    <button className={`${base} ${className}`} disabled={disabled || loading} {...props}>
      {loading && <Loader2 size={16} className="animate-spin" />}
      {children}
    </button>
  );
}

export function Field({ label, error, hint, children, required }) {
  return (
    <label className="block space-y-1.5">
      {label && (
        <span className="text-sm font-medium text-studio-text/90">
          {label} {required && <span className="text-reel">*</span>}
        </span>
      )}
      {children}
      {hint && !error && <span className="block text-xs text-studio-muted">{hint}</span>}
      {error && <span className="block text-xs text-danger">{error}</span>}
    </label>
  );
}

export function Input({ className = "", ...props }) {
  return <input className={`input-field ${className}`} {...props} />;
}

export function TextArea({ className = "", rows = 5, ...props }) {
  return <textarea rows={rows} className={`input-field resize-y ${className}`} {...props} />;
}

export function Select({ className = "", children, ...props }) {
  return (
    <select className={`input-field appearance-none cursor-pointer ${className}`} {...props}>
      {children}
    </select>
  );
}

export function Badge({ tone = "neutral", children }) {
  const tones = {
    neutral: "bg-studio-surface2 text-studio-muted border-studio-border",
    success: "bg-success/10 text-success border-success/30",
    warning: "bg-marquee/10 text-marquee border-marquee/30",
    danger: "bg-danger/10 text-danger border-danger/30",
    info: "bg-reel/10 text-reel border-reel/30",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function ProgressBar({ percent, tone = "marquee" }) {
  const barColor = tone === "marquee" ? "bg-marquee" : tone === "reel" ? "bg-reel" : "bg-success";
  return (
    <div className="w-full h-2 rounded-full bg-studio-surface2 overflow-hidden">
      <div
        className={`h-full ${barColor} transition-all duration-500 ease-out rounded-full`}
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}

export function Card({ className = "", children }) {
  return <div className={`card ${className}`}>{children}</div>;
}

export function Spinner({ size = 20, className = "" }) {
  return <Loader2 size={size} className={`animate-spin text-marquee ${className}`} />;
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center text-center gap-3 py-16 px-6">
      {Icon && (
        <div className="w-14 h-14 rounded-2xl bg-studio-surface2 flex items-center justify-center">
          <Icon size={26} className="text-marquee" />
        </div>
      )}
      <h3 className="font-display text-lg text-studio-text">{title}</h3>
      {description && <p className="text-sm text-studio-muted max-w-sm">{description}</p>}
      {action}
    </div>
  );
}
