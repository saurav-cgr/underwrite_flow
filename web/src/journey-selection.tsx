import { Button, PageHeading } from "./components";
import { Icon } from "./icons";
import type { JourneyType, Screen } from "./types";

interface JourneyOption {
  journey: JourneyType;
  title: string;
  description: string;
  icon: "plus" | "clock";
}

const OPTIONS: JourneyOption[] = [
  {
    journey: "new_business",
    title: "Start a new policy",
    description:
      "Apply for fictional coverage that does not exist on our books yet.",
    icon: "plus",
  },
  {
    journey: "renewal",
    title: "Renew a policy",
    description:
      "Continue fictional coverage using a prior policy as evidence.",
    icon: "clock",
  },
];

// Let an applicant choose new business or renewal before seeing products.
export function JourneySelection({
  onSelect,
  onNavigate,
}: {
  onSelect: (journey: JourneyType) => void;
  onNavigate: (screen: Screen) => void;
}) {
  return (
    <>
      <PageHeading
        eyebrow="New application"
        title="What are you applying for?"
        description={
          "Your choice decides which products and documents apply, "
          + "including a prior policy for a renewal."
        }
        action={
          <Button variant="quiet" onClick={() => onNavigate("dashboard")}>
            Back to overview
          </Button>
        }
      />
      <div className="product-grid" role="radiogroup" aria-label="Journey">
        {OPTIONS.map((option) => (
          <button
            aria-checked={false}
            className="product-card"
            key={option.journey}
            onClick={() => onSelect(option.journey)}
            role="radio"
            type="button"
          >
            <span className="product-icon">
              <Icon name={option.icon} />
            </span>
            <h2>{option.title}</h2>
            <p>{option.description}</p>
            <span className="select-line">
              <span aria-hidden="true" className="radio-mark" />
              Choose {option.title.toLowerCase()}
            </span>
          </button>
        ))}
      </div>
    </>
  );
}
