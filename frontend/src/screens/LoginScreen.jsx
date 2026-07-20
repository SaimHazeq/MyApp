import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clapperboard, Mail, Lock, User as UserIcon } from "lucide-react";
import { useAuth } from "../state/AuthContext";
import { Button, Field, Input } from "../widgets/common";
import { DecorativeFilmRail } from "../widgets/FilmRailStepper";
import { isValidEmail, isStrongEnoughPassword } from "../utils/validators";
import { toast } from "../state/useToastStore";

export default function LoginScreen() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const validate = () => {
    const e = {};
    if (mode === "register" && fullName.trim().length < 2) e.fullName = "Enter your name.";
    if (!isValidEmail(email)) e.email = "Enter a valid email address.";
    if (!isStrongEnoughPassword(password)) e.password = "Password must be at least 8 characters.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (evt) => {
    evt.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ email, password });
      } else {
        await register({ fullName, email, password });
      }
      navigate("/home", { replace: true });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative px-4 py-10">
      <div className="absolute left-4 top-0 bottom-0 hidden lg:block">
        <DecorativeFilmRail count={16} />
      </div>
      <div className="absolute right-4 top-0 bottom-0 hidden lg:block">
        <DecorativeFilmRail count={16} />
      </div>

      <div className="w-full max-w-md">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-marquee flex items-center justify-center shadow-glow">
            <Clapperboard size={26} className="text-studio-bg" />
          </div>
          <h1 className="font-display text-2xl font-bold">AI Cartoon Movie Maker</h1>
          <p className="text-studio-muted text-sm">{mode === "login" ? "Welcome back, director." : "Create your studio account"}</p>
        </div>

        <div className="card p-6 sm:p-8 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-5">
            {mode === "register" && (
              <Field label="Full name" error={errors.fullName} required>
                <div className="relative">
                  <UserIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-studio-muted" />
                  <Input className="pl-9" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Director" />
                </div>
              </Field>
            )}

            <Field label="Email" error={errors.email} required>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-studio-muted" />
                <Input className="pl-9" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
              </div>
            </Field>

            <Field label="Password" error={errors.password} required hint={mode === "register" ? "At least 8 characters." : undefined}>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-studio-muted" />
                <Input className="pl-9" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
              </div>
            </Field>

            <Button type="submit" className="w-full" loading={submitting}>
              {mode === "login" ? "Log in" : "Create account"}
            </Button>
          </form>

          <p className="text-center text-sm text-studio-muted">
            {mode === "login" ? "New to the studio?" : "Already have an account?"}{" "}
            <button
              className="text-marquee font-medium hover:underline"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
            >
              {mode === "login" ? "Create an account" : "Log in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
