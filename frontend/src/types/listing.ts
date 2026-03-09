export interface Listing {
  id: number;
  external_id: string | null;
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
  zillow_url: string | null;
  mls_number: string | null;
}

export interface WeightAdjustments {
  location_weight_boost: number;
  price_weight_boost: number;
  lot_size_weight_boost: number;
  layout_weight_boost: number;
  basement_weight_boost: number;
}

export interface ScoreBreakdown {
  must_have_checks: Record<string, { pass: boolean; reason: string }>;
  nice_to_have_details: Record<string, { score: number; reason: string }>;
  must_have_rate: number;
  must_have_satisfaction: number;
  nice_to_have_satisfaction: number;
  scoring_mode: string;
  weights: { must_have: number; nice_to_have: number };
  weight_adjustments?: WeightAdjustments;
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
  rejection_reason: string | null;
  rejection_details: string | null;
  sent_to_client: boolean;
}
