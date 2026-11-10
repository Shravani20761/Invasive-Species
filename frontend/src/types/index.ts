export type Role = "citizen" | "researcher" | "admin";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
};

export type Species = {
  id: number;
  common_name: string;
  scientific_name: string;
  category: "plant" | "animal";
  classification: "invasive" | "native" | "unknown";
  description: string;
  risk_level: string;
  characteristics: string;
  reference_image: string | null;
  distribution: string;
  is_demonstration: boolean;
  sighting_count: number;
};

export type Prediction = {
  model_name: string;
  model_version: string;
  inference_mode: string;
  pipeline: string;
  predicted_label: string;
  scientific_name: string;
  confidence: number;
  insufficient_confidence: boolean;
  classification: string;
};

export type Verification = {
  id: number;
  action: string;
  comment: string;
  previous_status: string;
  new_status: string;
  reviewer_name: string;
  created_at: string;
};

export type Sighting = {
  id: number;
  user_id: number;
  observer_name: string;
  species_id: number | null;
  common_name: string;
  scientific_name: string | null;
  classification: string;
  category: string | null;
  image_url: string;
  latitude: number;
  longitude: number;
  location_name: string;
  observed_at: string;
  created_at: string;
  confidence: number | null;
  verification_status: string;
  risk_level: string | null;
  submitted_name: string;
  notes: string;
  is_demonstration: boolean;
  insufficient_confidence: boolean;
  prediction: Prediction | null;
  verification_history: Verification[];
};

export type Cluster = {
  id: number;
  species_id: number | null;
  common_name: string;
  scientific_name: string | null;
  classification: string;
  sighting_count: number;
  center_latitude: number;
  center_longitude: number;
  radius_km: number;
  first_detected: string;
  last_detected: string;
  growth_indicator: string;
  growth_ratio: number;
  risk_level: string;
  sighting_ids: number[];
};

export type AlertItem = {
  id: number;
  species_id: number | null;
  common_name: string | null;
  scientific_name: string | null;
  cluster_id: number | null;
  alert_type: string;
  risk_level: string;
  title: string;
  description: string;
  reason: string;
  location_name: string;
  latitude: number | null;
  longitude: number | null;
  status: string;
  created_at: string;
  reviewed_at: string | null;
  review_comment: string;
};

export type IdentifyResult = {
  inference_mode: string;
  model_name: string;
  model_version: string;
  demo_notice: string;
  predicted_common_name: string;
  scientific_name: string;
  category: string;
  classification: string;
  confidence: number;
  confidence_percent: number;
  insufficient_confidence: boolean;
  risk_level: string | null;
  description: string;
  characteristics: string;
  recommended_verification_status: string;
  message: string;
  species_id: number | null;
  pipeline?: string;
  alternatives: { common_name: string; scientific_name: string; confidence: number; category: string }[];
  detections: {
    detector: string;
    note?: string;
    boxes: { label: string; score: number | null; x: number; y: number; width: number; height: number }[];
  };
};

export type Overview = {
  total_sightings: number;
  invasive_species: number;
  verified_reports: number;
  active_clusters: number;
  pending_reports: number;
  rejected_reports: number;
  open_alerts: number;
  recent_sightings: Sighting[];
  species_distribution: { name: string; count: number }[];
  category_distribution: { name: string; value: number }[];
  active_alerts: AlertItem[];
  emerging_clusters: Cluster[];
  demonstration_records: number;
  data_notice: string | null;
};

export type Page<T> = { items: T[]; total: number; page?: number; page_size?: number };
