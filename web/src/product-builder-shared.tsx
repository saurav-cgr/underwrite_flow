// Small controls shared across the guided product-builder section editors.
import type { JourneyType } from "./types";

// Toggle one journey inside a stable applies_to selection.
export function toggleJourney(
  appliesTo: JourneyType[],
  journey: JourneyType,
): JourneyType[] {
  return appliesTo.includes(journey)
    ? appliesTo.filter((item) => item !== journey)
    : [...appliesTo, journey];
}

// Return the applicant-facing label for one journey type.
function journeyLabel(journey: JourneyType): string {
  return journey === "new_business" ? "New business" : "Renewal";
}

// Render checkboxes for which supported journeys one entry applies to.
export function AppliesToEditor({
  appliesTo,
  onChange,
  supported,
}: {
  appliesTo: JourneyType[];
  onChange: (next: JourneyType[]) => void;
  supported: JourneyType[];
}) {
  return (
    <fieldset className="field">
      <legend>Applies to</legend>
      {supported.map((journey) => (
        <label className="field-inline" key={journey}>
          <input
            checked={appliesTo.includes(journey)}
            onChange={() => onChange(toggleJourney(appliesTo, journey))}
            type="checkbox"
          />
          {journeyLabel(journey)}
        </label>
      ))}
    </fieldset>
  );
}

// Render checkboxes for which journeys a document is required for, using
// label text distinct from AppliesToEditor's so both stay unambiguous.
export function RequiredForEditor({
  requiredFor,
  onChange,
  supported,
}: {
  requiredFor: JourneyType[];
  onChange: (next: JourneyType[]) => void;
  supported: JourneyType[];
}) {
  return (
    <fieldset className="field">
      <legend>Required for</legend>
      {supported.map((journey) => (
        <label className="field-inline" key={journey}>
          <input
            checked={requiredFor.includes(journey)}
            onChange={() => onChange(toggleJourney(requiredFor, journey))}
            type="checkbox"
          />
          {`Required for ${journeyLabel(journey).toLowerCase()}`}
        </label>
      ))}
    </fieldset>
  );
}

// Parse a typed comparison value as a number or boolean when it looks like
// one, so condition editors preserve the applicant field's real type.
export function parseComparisonValue(
  raw: string,
): string | number | boolean {
  if (raw.trim() === "") return raw;
  if (raw === "true" || raw === "false") return raw === "true";
  const numeric = Number(raw);
  return Number.isNaN(numeric) ? raw : numeric;
}
