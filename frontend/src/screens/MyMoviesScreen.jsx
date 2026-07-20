import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PlusCircle, Search, Film, Trash2 } from "lucide-react";
import { AppShell } from "../widgets/AppShell";
import { Button, Card, EmptyState, Input, Select } from "../widgets/common";
import { MovieCard } from "../widgets/MovieCard";
import { ConfirmModal } from "../widgets/Modal";
import { useProjectStore } from "../state/useProjectStore";
import { toast } from "../state/useToastStore";

const STATUS_FILTERS = [
  { value: "all", label: "All" },
  { value: "completed", label: "Ready" },
  { value: "draft", label: "Drafts" },
  { value: "failed", label: "Failed" },
  { value: "generating", label: "Generating" },
];

export default function MyMoviesScreen() {
  const { projects, projectsLoading, fetchProjects, removeProject } = useProjectStore();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  const filtered = useMemo(() => {
    return projects.filter((p) => {
      const matchesQuery = p.title?.toLowerCase().includes(query.toLowerCase());
      const matchesStatus =
        statusFilter === "all" ? true
        : statusFilter === "generating" ? !["draft", "completed", "failed"].includes(p.status)
        : p.status === statusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [projects, query, statusFilter]);

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await removeProject(pendingDelete.id);
      toast.success("Movie deleted.");
    } catch {
      toast.error("Couldn't delete this movie.");
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  };

  return (
    <AppShell
      title="My Movies"
      subtitle={`${projects.length} project${projects.length === 1 ? "" : "s"}`}
      actions={
        <Link to="/create">
          <Button><PlusCircle size={16} /> New movie</Button>
        </Link>
      }
    >
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-studio-muted" />
          <Input className="pl-9" placeholder="Search your movies…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <Select className="sm:w-48" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_FILTERS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
        </Select>
      </div>

      {projectsLoading ? (
        <p className="text-studio-muted text-sm">Loading…</p>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState icon={Film} title="No movies match" description="Try a different search or filter, or start a brand new project." />
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {filtered.map((p) => (
            <div key={p.id} className="relative group">
              <MovieCard project={p} />
              <button
                onClick={(e) => { e.preventDefault(); setPendingDelete(p); }}
                className="absolute top-2 left-2 w-8 h-8 rounded-lg bg-studio-bg/80 backdrop-blur flex items-center justify-center text-studio-muted hover:text-danger opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={Boolean(pendingDelete)}
        title="Delete this movie?"
        description={`"${pendingDelete?.title}" and all of its generated assets will be permanently deleted.`}
        confirmLabel="Delete"
        danger
        loading={deleting}
        onConfirm={handleDelete}
        onClose={() => setPendingDelete(null)}
      />
    </AppShell>
  );
}
