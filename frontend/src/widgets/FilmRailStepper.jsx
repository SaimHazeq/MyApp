/**
 * A vertical rail of sprocket holes, one per pipeline stage. Holes before
 * the current stage are filled (gold), the current stage pulses (coral),
 * and remaining stages stay hollow. Doubles as literal film-reel texture
 * and as a functional progress tracker - see when_to_use notes in
 * screens/GenerationProgressScreen.jsx.
 */
export function FilmRailStepper({ stages, currentIndex, orientation = "vertical" }) {
  const isVertical = orientation === "vertical";
  return (
    <div className={isVertical ? "film-rail h-full" : "flex items-center gap-3 px-4 py-2 rounded-full bg-studio-surface2/60 w-fit"}>
      {stages.map((_, i) => {
        const state = i < currentIndex ? "filled" : i === currentIndex ? "active" : "";
        return <div key={i} className={`sprocket-hole ${state}`} />;
      })}
    </div>
  );
}

/** Decorative-only variant with no semantic stage meaning, for Splash/Login brand texture. */
export function DecorativeFilmRail({ count = 10 }) {
  return (
    <div className="film-rail h-full">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`sprocket-hole ${i % 3 === 0 ? "filled" : ""}`} />
      ))}
    </div>
  );
}
