export interface ExtractedRequirement {
  id: number;
  transcript_id: number;
  client_id: number | null;
  client_name: string | null;
  budget_max: number | null;
  locations: string[];
  must_haves: string[];
  nice_to_haves: string[];
  property_type: string | null;
  min_beds: number | null;
  min_baths: number | null;
  min_sqft: number | null;
  school_requirement: string | null;
  timeline: string | null;
  financing_type: string | null;
  confidence_score: number | null;
  llm_provider: string | null;
  llm_model: string | null;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

export interface RequirementUpdate {
  client_name?: string;
  budget_max?: number;
  locations?: string[];
  must_haves?: string[];
  nice_to_haves?: string[];
  property_type?: string;
  min_beds?: number;
  min_baths?: number;
  min_sqft?: number;
  school_requirement?: string;
  timeline?: string;
  financing_type?: string;
}
