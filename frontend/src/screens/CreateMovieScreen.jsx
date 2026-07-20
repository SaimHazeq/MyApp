import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Plus, Trash2, Sparkles, Check } from "lucide-react";
import { AppShell } from "../widgets/AppShell";
import { Button, Card, Field, Input, Select, TextArea, Badge } from "../widgets/common";
import { useProjectStore } from "../state/useProjectStore";
import { projectService } from "../services/projectService";
import { generationService } from "../services/generationService";
import { toast } from "../state/useToastStore";
import { ANIMATION_STYLES, CHARACTER_ROLES, VOICE_PROFILES } from "../utils/constants";
import { validateMovieDraft } from "../utils/validators";

const STEPS = ["Concept", "Story", "Characters", "Dialogue", "Style & Duration", "Review"];

const emptyCharacter = () => ({ name: "", description: "", role: "supporting", voice_profile: "" });

export default function CreateMovieScreen() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { createProject } = useProjectStore();

  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [existingId, setExistingId] = useState(projectId || null);

  const [form, setForm] = useState({
    title: "",
    prompt: "",
    story: "",
    dialogue: "",
    characters: [emptyCharacter()],
    durationMinutes: 2,
    animationStyle: "3d_pixar",
    resolution: "1920x1080",
    voiceLanguage: "en-US",
  });

  useEffect(() => {
    if (!projectId) return;
    projectService.get(projectId).then((p) => {
      setForm({
        title: p.title,
        prompt: p.prompt,
        story: p.story,
        dialogue: p.dialogue,
        characters: p.characters?.length ? p.characters : [emptyCharacter()],
        durationMinutes: p.duration_minutes,
        animationStyle: p.animation_style,
        resolution: p.resolution,
        voiceLanguage: "en-US",
      });
    });
  }, [projectId]);

  const update = (patch) => setForm((f) => ({ ...f, ...patch }));

  const updateCharacter = (index, patch) => {
    const chars = [...form.characters];
    chars[index] = { ...chars[index], ...patch };
    update({ characters: chars });
  };

  const addCharacter = () => update({ characters: [...form.characters, emptyCharacter()] });
  const removeCharacter = (index) => update({ characters: form.characters.filter((_, i) => i !== index) });

  const goNext = () => {
    if (step === 1) {
      const draftErrors = validateMovieDraft({ title: form.title, story: form.story, durationMinutes: form.durationMinutes });
      setErrors(draftErrors);
      if (Object.keys(draftErrors).length) return;
    }
    setStep((s) => Math.min(STEPS.length - 1, s + 1));
  };
  const goBack = () => setStep((s) => Math.max(0, s - 1));

  const payload = useMemo(
    () => ({
      title: form.title,
      prompt: form.prompt,
      story: form.story,
      dialogue: form.dialogue,
      characters: form.characters
        .filter((c) => c.name.trim())
        .map((c) => ({ name: c.name, description: c.description, role: c.role, voice_profile: c.voice_profile || null })),
      duration_minutes: Number(form.durationMinutes),
      animation_style: form.animationStyle,
      resolution: form.resolution,
      voice_language: form.voiceLanguage,
    }),
    [form]
  );

  const handleGenerate = async () => {
    setSubmitting(true);
    try {
      let project;
      if (existingId) {
        project = await projectService.update(existingId, {
          title: payload.title,
          prompt: payload.prompt,
          story: payload.story,
          dialogue: payload.dialogue,
          duration_minutes: payload.duration_minutes,
          animation_style: payload.animation_style,
          resolution: payload.resolution,
        });
      } else {
        project = await createProject(payload);
        setExistingId(project.id);
      }
      await generationService.start(project.id);
      toast.success("Generation started!");
      navigate(`/generating/${project.id}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't start generation. Please check your inputs.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSaveDraft = async () => {
    setSubmitting(true);
    try {
      if (existingId) {
        await projectService.update(existingId, {
          title: payload.title, prompt: payload.prompt, story: payload.story, dialogue: payload.dialogue,
          duration_minutes: payload.duration_minutes, animation_style: payload.animation_style, resolution: payload.resolution,
        });
      } else {
        const project = await createProject(payload);
        setExistingId(project.id);
      }
      toast.success("Draft saved.");
      navigate("/movies");
    } catch {
      toast.error("Couldn't save draft.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell title="Create Movie" subtitle="Story to screen">
      {/* Step indicator */}
      <div className="flex items-center gap-1 mb-8 overflow-x-auto pb-1">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-1 shrink-0">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border transition-colors ${
                i < step ? "bg-marquee border-marquee text-studio-bg"
                : i === step ? "border-marquee text-marquee"
                : "border-studio-border text-studio-muted"
              }`}
            >
              {i < step ? <Check size={13} /> : i + 1}
            </div>
            <span className={`text-xs mr-2 ${i === step ? "text-studio-text font-medium" : "text-studio-muted"}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="w-6 h-px bg-studio-border" />}
          </div>
        ))}
      </div>

      <Card className="p-6 sm:p-8 max-w-3xl">
        {step === 0 && (
          <div className="space-y-5">
            <Field label="Movie title" required error={errors.title}>
              <Input value={form.title} onChange={(e) => update({ title: e.target.value })} placeholder="The Fox Who Chased Thunder" />
            </Field>
            <Field label="Prompt" hint="A one-line pitch. Guides tone, mood and pacing choices across the whole pipeline.">
              <TextArea rows={3} value={form.prompt} onChange={(e) => update({ prompt: e.target.value })}
                placeholder="A brave young fox learns courage during a forest thunderstorm." />
            </Field>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <Field label="Story" required error={errors.story} hint="Write in paragraphs — each paragraph becomes one scene. Mention locations, weather and actions so the AI can pick matching visuals, camera moves and sound effects.">
              <TextArea rows={12} value={form.story} onChange={(e) => update({ story: e.target.value })}
                placeholder={"Mira the fox tiptoed through the misty forest at dawn...\n\nThunder cracked overhead and rain began to pour..."} />
            </Field>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <p className="text-sm text-studio-muted">
              Every character gets a consistent look and voice across the entire movie, generated once and reused in every scene.
            </p>
            {form.characters.map((c, i) => (
              <div key={i} className="border border-studio-border rounded-xl p-4 space-y-3 relative">
                {form.characters.length > 1 && (
                  <button onClick={() => removeCharacter(i)} className="absolute top-3 right-3 text-studio-muted hover:text-danger">
                    <Trash2 size={16} />
                  </button>
                )}
                <div className="grid sm:grid-cols-2 gap-3">
                  <Field label="Name" required>
                    <Input value={c.name} onChange={(e) => updateCharacter(i, { name: e.target.value })} placeholder="Mira" />
                  </Field>
                  <Field label="Role">
                    <Select value={c.role} onChange={(e) => updateCharacter(i, { role: e.target.value })}>
                      {CHARACTER_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </Select>
                  </Field>
                </div>
                <Field label="Description" hint="Looks, personality, notable traits (e.g. 'tall, wears round glasses, curious and brave').">
                  <TextArea rows={2} value={c.description} onChange={(e) => updateCharacter(i, { description: e.target.value })} />
                </Field>
                <Field label="Voice" hint="Leave on Auto to let the AI pick a fitting voice for this role.">
                  <Select value={c.voice_profile} onChange={(e) => updateCharacter(i, { voice_profile: e.target.value })}>
                    <option value="">Auto (recommended)</option>
                    {VOICE_PROFILES.map((v) => <option key={v.value} value={v.value}>{v.label}</option>)}
                  </Select>
                </Field>
              </div>
            ))}
            <Button variant="secondary" onClick={addCharacter}><Plus size={16} /> Add character</Button>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <Field label="Dialogue script" hint={'Optional. Either a flat "NAME: line" script, or a full screenplay format with explicit scenes - e.g. "Scene 1 — Den at the forest edge", "SFX: distant thunder", "FIRA (soft, unsure): I\'ll watch from here.", "NARRATOR: ...". When scene headers are present they define the movie\'s scenes directly, and SFX/dialogue are matched to the exact scene they appear under.'}>
              <TextArea rows={10} value={form.dialogue} onChange={(e) => update({ dialogue: e.target.value })}
                placeholder={"Mira: Who's there? Show yourself!\nBoldo: Just me, friend. Why so scared?"} />
            </Field>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-6">
            <div>
              <p className="text-sm font-medium mb-3">Animation style</p>
              <div className="grid sm:grid-cols-2 gap-3">
                {ANIMATION_STYLES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => update({ animationStyle: s.value })}
                    className={`text-left p-4 rounded-xl border transition-colors ${
                      form.animationStyle === s.value ? "border-marquee bg-marquee/10" : "border-studio-border hover:border-marquee/40"
                    }`}
                  >
                    <p className="font-medium text-sm">{s.label}</p>
                    <p className="text-xs text-studio-muted mt-1">{s.blurb}</p>
                  </button>
                ))}
              </div>
            </div>

            <Field label={`Duration: ${form.durationMinutes} min`} error={errors.durationMinutes}>
              <input
                type="range" min={0.5} max={30} step={0.5}
                value={form.durationMinutes}
                onChange={(e) => update({ durationMinutes: Number(e.target.value) })}
                className="w-full accent-marquee"
              />
            </Field>

            <Field label="Resolution">
              <Select value={form.resolution} onChange={(e) => update({ resolution: e.target.value })}>
                <option value="1280x720">720p</option>
                <option value="1920x1080">1080p (recommended)</option>
                <option value="3840x2160">4K</option>
              </Select>
            </Field>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-5">
            <div className="flex items-center gap-2 text-marquee">
              <Sparkles size={18} />
              <p className="font-medium">Ready to generate</p>
            </div>
            <dl className="grid sm:grid-cols-2 gap-4 text-sm">
              <div><dt className="text-studio-muted">Title</dt><dd className="font-medium">{form.title || "—"}</dd></div>
              <div><dt className="text-studio-muted">Duration</dt><dd className="font-medium">{form.durationMinutes} minutes</dd></div>
              <div><dt className="text-studio-muted">Style</dt><dd className="font-medium">{ANIMATION_STYLES.find((s) => s.value === form.animationStyle)?.label}</dd></div>
              <div><dt className="text-studio-muted">Resolution</dt><dd className="font-medium">{form.resolution}</dd></div>
            </dl>
            <div>
              <p className="text-studio-muted text-sm mb-2">Characters</p>
              <div className="flex flex-wrap gap-2">
                {form.characters.filter((c) => c.name).map((c, i) => <Badge key={i}>{c.name}</Badge>)}
                {!form.characters.some((c) => c.name) && <span className="text-sm text-studio-muted">None added</span>}
              </div>
            </div>
            <div className="bg-studio-surface2 rounded-xl p-4 text-sm text-studio-muted">
              Generation runs through story analysis, character & environment generation, animation, voice & lip
              sync, music/SFX, and final rendering — you'll see live progress on the next screen.
            </div>
          </div>
        )}

        {/* Nav buttons */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-studio-border">
          <Button variant="secondary" onClick={goBack} disabled={step === 0}>
            <ArrowLeft size={16} /> Back
          </Button>
          <div className="flex gap-3">
            {step === STEPS.length - 1 ? (
              <>
                <Button variant="secondary" onClick={handleSaveDraft} loading={submitting}>Save as draft</Button>
                <Button onClick={handleGenerate} loading={submitting}>
                  <Sparkles size={16} /> Generate movie
                </Button>
              </>
            ) : (
              <Button onClick={goNext}>Next <ArrowRight size={16} /></Button>
            )}
          </div>
        </div>
      </Card>
    </AppShell>
  );
}
