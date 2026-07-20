import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Clapperboard } from "lucide-react";
import { useAuth } from "../state/AuthContext";
import { DecorativeFilmRail } from "../widgets/FilmRailStepper";

export default function SplashScreen() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    const timer = setTimeout(() => navigate(user ? "/home" : "/login", { replace: true }), 1600);
    return () => clearTimeout(timer);
  }, [loading, user, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="absolute left-6 top-0 bottom-0 hidden sm:block">
        <DecorativeFilmRail count={14} />
      </div>
      <div className="absolute right-6 top-0 bottom-0 hidden sm:block">
        <DecorativeFilmRail count={14} />
      </div>

      <div className="flex flex-col items-center gap-5 animate-[fadeIn_0.6s_ease-out]">
        <div className="w-20 h-20 rounded-3xl bg-marquee flex items-center justify-center shadow-glow animate-sprocketPulse">
          <Clapperboard size={40} className="text-studio-bg" />
        </div>
        <div className="text-center">
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight">
            AI Cartoon <span className="text-marquee">Movie Maker</span>
          </h1>
          <p className="text-studio-muted mt-2 label-eyebrow">Your story. Fully animated.</p>
        </div>
        <div className="w-40 h-1 rounded-full bg-studio-surface2 overflow-hidden mt-4">
          <div className="h-full bg-reel animate-[loadingBar_1.4s_ease-in-out_infinite]" style={{ width: "40%" }} />
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px);} to { opacity: 1; transform: translateY(0);} }
        @keyframes loadingBar { 0% { margin-left: -40%; } 100% { margin-left: 100%; } }
      `}</style>
    </div>
  );
}
