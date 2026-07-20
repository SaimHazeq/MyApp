export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const ANIMATION_STYLES = [
  { value: "3d_pixar", label: "3D Pixar-style", blurb: "Warm, rounded, family-friendly 3D" },
  { value: "3d_stylized", label: "3D Stylized", blurb: "Bold stylized 3D with strong silhouettes" },
  { value: "3d_realistic", label: "3D Semi-Realistic", blurb: "Higher-fidelity proportions & lighting" },
  { value: "anime_3d", label: "Anime 3D Hybrid", blurb: "Cel-shaded anime look in 3D space" },
  { value: "claymation", label: "Claymation", blurb: "Stop-motion clay aesthetic" },
];

export const VOICE_PROFILES = [
  { value: "warm_confident", label: "Warm & Confident" },
  { value: "young_bright_optimistic", label: "Young & Bright" },
  { value: "brave_energetic", label: "Brave & Energetic" },
  { value: "deep_menacing", label: "Deep & Menacing" },
  { value: "cold_calculating", label: "Cold & Calculating" },
  { value: "gravelly_villain", label: "Gravelly Villain" },
  { value: "friendly_neutral", label: "Friendly & Neutral" },
  { value: "quirky_comic", label: "Quirky & Comic" },
  { value: "gentle_wise_elder", label: "Gentle Wise Elder" },
];

export const CHARACTER_ROLES = [
  { value: "protagonist", label: "Protagonist" },
  { value: "antagonist", label: "Antagonist" },
  { value: "supporting", label: "Supporting" },
];

// Mirrors backend app/schemas/generation.py PIPELINE_STAGES - keep in sync.
export const PIPELINE_STAGES = [
  { key: "queued", label: "Queued" },
  { key: "analyzing_story", label: "Analyzing story & splitting scenes" },
  { key: "generating_characters", label: "Generating 3D characters" },
  { key: "generating_environments", label: "Building environments" },
  { key: "generating_voice", label: "Generating AI voices & lip sync data" },
  { key: "animating", label: "Animating actions, camera moves & lip sync" },
  { key: "generating_audio", label: "Composing music & sound effects" },
  { key: "rendering", label: "Rendering final video" },
  { key: "completed", label: "Completed" },
];

export const SFX_CATEGORIES = [
  "footsteps", "rain", "thunder", "wind", "birds",
  "explosions", "doors", "vehicles", "animals",
];

export const EXPORT_PRESETS = [
  { value: "mp4_1080p", label: "MP4 - 1080p", hint: "Recommended for most platforms" },
  { value: "mp4_720p", label: "MP4 - 720p", hint: "Smaller file, faster upload" },
  { value: "mp4_4k", label: "MP4 - 4K", hint: "Studio quality, largest file" },
];
