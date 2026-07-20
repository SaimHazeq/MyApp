import { useEffect } from "react";
import { Link } from "react-router-dom";
import { PlusCircle, Film, Clock, Sparkles } from "lucide-react";
import { AppShell } from "../widgets/AppShell";
import { Button, Card, EmptyState } from "../widgets/common";
import { MovieCard } from "../widgets/MovieCard";
import { useProjectStore } from "../state/useProjectStore";
import { useAuth } from "../state/AuthContext";

export default function HomeScreen() {
  const { projects, projectsLoading, fetchProjects } = useProjectStore();
  const { user } = useAuth();

  useEffect(() => {
    fetchProjects();
  }, []);

  const completed = projects.filter((p) => p.status === "completed");
  const totalMinutes = completed.reduce((sum, p) => sum + (p.duration_minutes || 0), 0);

  return (
    <AppShell title={`Welcome back, ${user?.full_name?.split(" ")[0] || "Director"}`} subtitle="Studio overview">
      {/* Hero */}
      <div className="card p-8 sm:p-10 mb-8 relative overflow-hidden">
        <div className="absolute -right-10 -top-10 w-56 h-56 bg-marquee/10 rounded-full blur-3xl" />
        <div className="absolute -left-10 -bottom-10 w-56 h-56 bg-reel/10 rounded-full blur-3xl" />
        <div className="relative max-w-xl">
          <p className="label-eyebrow mb-3">Now showing: your imagination</p>
          <h2 className="font-display text-3xl font-bold mb-3">Turn any story into a fully animated 3D movie</h2>
          <p className="text-studio-muted mb-6">
            Write a prompt, story, dialogue and characters — the AI pipeline handles scene splitting,
            consistent characters, environments, camera work, lip-synced voices, music and sound effects,
            all the way to a downloadable MP4.
          </p>
          <Link to="/create">
            <Button className="text-base px-6 py-3">
              <PlusCircle size={18} /> Create a new movie
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <Card className="p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-marquee/15 flex items-center justify-center"><Film size={20} className="text-marquee" /></div>
          <div>
            <p className="text-2xl font-display font-bold">{projects.length}</p>
            <p className="text-xs text-studio-muted">Total projects</p>
          </div>
        </Card>
        <Card className="p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-success/15 flex items-center justify-center"><Sparkles size={20} className="text-success" /></div>
          <div>
            <p className="text-2xl font-display font-bold">{completed.length}</p>
            <p className="text-xs text-studio-muted">Movies rendered</p>
          </div>
        </Card>
        <Card className="p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-reel/15 flex items-center justify-center"><Clock size={20} className="text-reel" /></div>
          <div>
            <p className="text-2xl font-display font-bold">{totalMinutes.toFixed(1)}</p>
            <p className="text-xs text-studio-muted">Minutes of animation</p>
          </div>
        </Card>
      </div>

      {/* Recent movies */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display text-lg font-semibold">Recent movies</h3>
        {projects.length > 0 && (
          <Link to="/movies" className="text-sm text-marquee hover:underline">View all</Link>
        )}
      </div>

      {projectsLoading ? (
        <p className="text-studio-muted text-sm">Loading your projects…</p>
      ) : projects.length === 0 ? (
        <Card>
          <EmptyState
            icon={Film}
            title="No movies yet"
            description="Start your first AI-generated cartoon movie in minutes."
            action={
              <Link to="/create">
                <Button><PlusCircle size={16} /> Create your first movie</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {projects.slice(0, 4).map((p) => (
            <MovieCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </AppShell>
  );
}
