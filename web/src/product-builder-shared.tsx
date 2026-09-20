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
          {journey === "new_business" ? "New business" : "Renewal"}
        </label>
      ))}
    </fieldset>
  );
}
