export default function formatEstimatedValue(value) {
  if (
    value === null ||
    value === undefined ||
    (typeof value === "string" && value.trim() === "")
  ) {
    return "—";
  }

  const numericValue = Number(String(value).replace(/,/g, "").trim());
  if (!Number.isFinite(numericValue)) {
    return value;
  }

  if (numericValue >= 1_000_000_000) {
    return `${(numericValue / 1_000_000_000).toFixed(2)}B`;
  }

  if (numericValue >= 1_000_000) {
    return `${(numericValue / 1_000_000).toFixed(2)}M`;
  }

  if (numericValue >= 1_000) {
    return `${(numericValue / 1_000).toFixed(2)}K`;
  }

  return value;
}
