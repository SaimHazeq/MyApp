import { X } from "lucide-react";
import { Button } from "./common";

export function Modal({ open, title, children, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="card w-full max-w-md p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-studio-muted hover:text-studio-text">
          <X size={18} />
        </button>
        {title && <h3 className="font-display text-lg font-semibold mb-3 pr-6">{title}</h3>}
        {children}
      </div>
    </div>
  );
}

export function ConfirmModal({ open, title, description, confirmLabel = "Confirm", danger, onConfirm, onClose, loading }) {
  return (
    <Modal open={open} title={title} onClose={onClose}>
      <p className="text-sm text-studio-muted mb-6">{description}</p>
      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={loading}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
