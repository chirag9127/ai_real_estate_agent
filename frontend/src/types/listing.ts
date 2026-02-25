export interface Listing {
  id: number;
  external_id: string | null;
  source: string | null;
  address: string | null;
  price: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  sqft: number | null;
  property_type: string | null;
  description: string | null;
  neighborhood: string | null;
  image_url: string | null;
  year_built: number | null;
  days_on_market: number | null;
  listing_url: string | null;
}

export interface ScoreBreakdown {
  must_have_checks: Record<string, { pass: boolean; reason: string }>;
  nice_to_have_details: Record<string, { score: number; reason: string }>;
  must_have_rate: number;
  weights: { must_have: number; nice_to_have: number };
}

export interface RankedListing {
  id: number;
  listing: Listing;
  overall_score: number | null;
  must_have_pass: boolean | null;
  nice_to_have_score: number | null;
  rank_position: number | null;
  score_breakdown: ScoreBreakdown | null;
  approved_by_harry: boolean | null;
  sent_to_client: boolean;
}
