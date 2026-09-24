function firstAvailable(...values) {
  return (
    values.find(
      (value) =>
        value !== undefined &&
        value !== null &&
        value !== ""
    ) ?? null
  );
}

function normalizeDate(value) {
  if (!value) return null;

  return String(value);
}

export function normalizeTender(tender) {
  // Normalize source so accidental whitespace does not
  // prevent the correct portal branch from being selected.
  const source = String(
    tender.source ?? ""
  ).trim();

  const normalized = {
    id: tender.id,
    source,

    // Main table fields
    tenderNo: null,
    referenceNo: null,
    tenderName: null,
    authority: null,
    organization: null,
    location: null,
    city: null,

    estimatedValue: null,
    bidSecurity: null,

    closingDate: null,
    advertisedDate: null,
    openingDate: null,

    capability:
      tender.relevance?.matched_capabilities ?? [],

    matchedKeywords:
      tender.relevance?.matched_keywords ?? [],

    relevanceScore:
      tender.relevance?.keyword_score ?? null,

    status: null,

    // Complete original tender data
    raw: tender,
  };

  // ==================================================
  // FEDERAL PPRA
  // ==================================================

  if (source === "Federal PPRA") {
    normalized.tenderNo =
      tender.web_tender_no;

    normalized.referenceNo =
      tender[
        "Tender No / Reference No / Tender Inquiry No"
      ];

    normalized.tenderName =
      tender["Tender Title"];

    normalized.authority =
      tender["Office Name"];

    normalized.organization =
      tender["Organization Name"];

    normalized.location =
      firstAvailable(
        tender["Office Address"],
        tender["City"]
      );

    normalized.city =
      tender["City"] ?? null;

    normalized.estimatedValue =
      firstAvailable(
        tender["Estimated Value"],
        tender["Estimated Cost"],
        tender["Cost"]
      );

    // Keep Bid Security separate from Estimated Value
    normalized.bidSecurity =
      tender["Bid Security"];

    normalized.advertisedDate =
      normalizeDate(
        tender["Advertisement Date"]
      );

    normalized.closingDate =
      normalizeDate(
        tender["Closing Date & Time"]
      );

    // Opening Time is a time-only field.
    // Do not convert it into a JavaScript Date.
    normalized.openingDate =
      tender["Opening Time"] ?? null;

    normalized.status =
      firstAvailable(
        tender["Status"],
        tender["Tender Status"]
      );
  }

  // ==================================================
  // PUNJAB PPRA
  // ==================================================

  else if (source === "Punjab PPRA") {
    normalized.tenderNo =
      tender.tender_number;

    normalized.referenceNo =
      firstAvailable(
        tender.tender_reference_no,
        tender.reference_no,
        tender.reference_number
      );

    normalized.tenderName =
      firstAvailable(
        tender.tender_details,
        tender.procurement_title
      );

    normalized.authority =
      firstAvailable(
        tender.authority,
        tender.authority_name
      );

    normalized.organization =
      tender.organization_details;

    normalized.location =
      firstAvailable(
        tender.location,
        tender.city,
        tender.district
      );

    normalized.city =
      firstAvailable(
        tender.city,
        tender.district
      );

    normalized.estimatedValue =
      firstAvailable(
        tender.estimated_value,
        tender.estimated_cost,
        tender.est_cost
      );

    // Do not mix Bid Security with Estimated Value
    normalized.bidSecurity =
      firstAvailable(
        tender.bid_security,
        tender.earnest_money
      );

    normalized.advertisedDate =
      normalizeDate(
        tender.advertised_date
      );

    normalized.closingDate =
      normalizeDate(
        tender.closing_date
      );

    // Preserve opening date/time as supplied by Punjab.
    normalized.openingDate =
      tender.opening_date ?? null;

    normalized.status =
      tender.status;
  }

  // ==================================================
  // BALOCHISTAN PPRA
  // ==================================================

  else if (source === "Balochistan PPRA") {
    normalized.tenderNo =
      tender.TSENumber;

    normalized.referenceNo =
      firstAvailable(
        tender.TenderNum,
        tender.TenderId
      );

    normalized.tenderName =
      firstAvailable(
        tender.TenderName,
        tender.Name,
        tender.TenderTitle
      );

    normalized.authority =
      tender.Agency;

    normalized.organization =
      tender.Department;

    normalized.location =
      firstAvailable(
        tender.District,
        tender.Address
      );

    normalized.city =
      tender.District || null;

    normalized.estimatedValue =
      firstAvailable(
        tender.EstCost,
        tender.Cost,
        tender.ActualCost
      );

    // EarnestMoney is the relevant field for Bid Security.
    // BidValidity is NOT Bid Security.
    normalized.bidSecurity =
      tender.EarnestMoney;

    normalized.advertisedDate =
      normalizeDate(
        firstAvailable(
          tender.PublishedDate,
          tender.AdvertisementDate,
          tender.AddDate
        )
      );

    normalized.closingDate =
      normalizeDate(
        firstAvailable(
          tender.CloseDate,
          tender.RevisedSubmissionLastDate
        )
      );

    // Preserve opening time/date as supplied by the portal.
    // Do not force it through normalizeDate because
    // OpenTime may be a time/epoch representation.
    normalized.openingDate =
      firstAvailable(
        tender.OpenTime,
        tender.RevisedBidsOpeningDate
      );

    normalized.status =
      firstAvailable(
        tender.TenderStatus,
        tender.Status
      );
  }

  // ==================================================
  // KP PPRA
  // ==================================================

  else if (source === "KP PPRA") {
    normalized.tenderNo =
      tender.tender_number;

    normalized.referenceNo =
      tender.tender_number;

    normalized.tenderName =
      tender.tender_details;

    normalized.authority =
      tender.organization_details;

    normalized.organization =
      tender.organization_details;

    normalized.location =
      null;

    normalized.city =
      null;

    normalized.estimatedValue =
      null;

    normalized.bidSecurity =
      null;

    normalized.advertisedDate =
      normalizeDate(
        tender.advertised_date
      );

    normalized.closingDate =
      normalizeDate(
        tender.closing_date
      );

    normalized.openingDate =
      null;

    normalized.status =
      null;
  }

  // ==================================================
  // SINDH PPRA
  // ==================================================

  else if (source === "Sindh PPRA") {
    normalized.tenderNo =
      tender.tenderNumber;

    normalized.referenceNo =
      tender.tenderNumbers;

    normalized.tenderName =
      tender.name;

    normalized.authority =
      tender.departmentName;

    normalized.organization =
      tender.departmentName;

    normalized.location =
      tender.location;

    normalized.city =
      tender.location;

    normalized.estimatedValue =
      tender.estimatedCost;

    normalized.bidSecurity =
      null;

    normalized.advertisedDate =
      normalizeDate(
        tender.publishDate
      );

    normalized.closingDate =
      normalizeDate(
        tender.lastSubmissionDate
      );

    normalized.openingDate =
      normalizeDate(
        tender.bidOpeningDate
      );

    normalized.status =
      tender.statusName;
  }

  return normalized;
}

export function normalizeTenders(tenders) {
  return tenders.map(normalizeTender);
}