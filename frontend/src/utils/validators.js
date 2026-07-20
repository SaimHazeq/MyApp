export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email || "");
}

export function isStrongEnoughPassword(password) {
  return (password || "").length >= 8;
}

export function required(value) {
  return typeof value === "string" ? value.trim().length > 0 : value != null;
}

export function validateMovieDraft({ title, story, durationMinutes }) {
  const errors = {};
  if (!required(title)) errors.title = "Give your movie a title.";
  if (!required(story) || story.trim().length < 20) {
    errors.story = "Add a bit more story (at least a couple of sentences).";
  }
  if (!durationMinutes || durationMinutes < 0.5 || durationMinutes > 30) {
    errors.durationMinutes = "Duration must be between 0.5 and 30 minutes.";
  }
  return errors;
}

export function formatDuration(minutes) {
  const totalSeconds = Math.round(minutes * 60);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function formatDate(isoString) {
  try {
    return new Date(isoString).toLocaleDateString(undefined, {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch {
    return "";
  }
}
