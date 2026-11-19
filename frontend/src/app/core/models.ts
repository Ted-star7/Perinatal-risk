export interface Session {
  token: string;
  is_owner?: boolean;
  doctor_id: number;
  doctor_name: string;
  clinic_id: number;
  clinic_name: string;
}

export interface RegisterBody {
  clinic_name: string;
  country?: string;
  type?: string;
  county?: string;
  phone?: string;
  doctor_name: string;
  email: string;
  password: string;
}

export interface LoginBody {
  email: string;
  password: string;
}

export interface PredictRequest {
  request_id?: string;
  assessment_token?: string;
  patient_ref: string;
  age?: number;
  age_at_start?: number;
  parity: number;
  first_pregnancy?: boolean;
  interval_months?: number | null;
  previous_stillbirth: boolean;
  previous_loss: boolean;
  multiple: boolean;
  baby_count?: number;
  pregnancy_id?: number | null;
  birth_spacing_months?: number | null;
  told_high_bp?: boolean;
  anc_visits?: number | null;
  education?: 'No education' | 'Primary' | 'Secondary' | 'Higher' | null;
  urine_tested?: boolean | null;
  iron_tablets?: boolean | null;
}

export interface OutcomeResult {
  status: 'available' | 'unavailable';
  label: string;
  description: string;
  score: number | null;
  model_id: string | null;
  message: string;
  prediction_context?: string | null;
  calibrated?: boolean;
  used_inputs?: string[];
}

export interface AssessmentResult {
  assessment_token?: string | null;
  perinatal: OutcomeResult;
  lbw: OutcomeResult;
  baseline: {
    flagged: boolean;
    factors: string[];
    unknown_factors: string[];
    summary: string;
  };
  recommendation: string;
  notes: string[];
}

export interface Driver {
  label: string;
  weight: number;
}

export interface PredictResponse {
  id: number;
  risk: number;
  risk_band: 'low' | 'moderate' | 'high' | 'unclassified';
  top_drivers: Driver[];
  recommendation: string;
  created_at: string;
  patient_ref?: string;
  assessment?: AssessmentResult | null;
  outcomes?: BirthOutcome[];
  multiple?: boolean;
  baby_count?: number | null;
  pregnancy_id?: number;
  birth_spacing_months?: number | null;
}

/** One model's result from the shared /metrics store (one row per cohort+algorithm). */
export interface MetricsRow {
  cohort: string;
  algorithm: string;
  pr_auc: number;
  roc_auc: number;
  recall_at_flag: number;
  beats_checklist: boolean;
  is_best: boolean;
  test_events: number;
  updated_at: string;
}

export interface BirthOutcomeInput {
  baby_number: number;
  expected_version: number;
  birth_date: string | null;
  observed_on: string;
  utc_offset_minutes?: number;
  status: 'unknown' | 'alive' | 'stillbirth' | 'died';
  death_age_days: number | null;
  birth_weight_grams: number | null;
  source: string;
  notes: string;
}
export interface BirthOutcome extends BirthOutcomeInput {
  version: number;
  doctor_id: number;
  recorded_at: string;
}

export interface PatientLookup {
  found: boolean;
  assessment_count: number;
  latest: PredictResponse | null;
  inputs: Partial<PredictRequest> | null;
}
export interface OutcomeSummary {
  pregnancies: number;
  babies: number;
  pregnancies_without_baby_count: number;
  survival: { pending: number; alive: number; stillbirth: number; died: number };
  birth_weight: { below_2500: number; at_least_2500: number; unknown: number };
  synthetic_excluded: boolean;
}
