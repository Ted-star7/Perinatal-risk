export interface Session {
  token: string;
  doctor_id: number;
  doctor_name: string;
  clinic_id: number;
  clinic_name: string;
}

export interface RegisterBody {
  clinic_name: string;
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
  patient_ref?: string;
  age: number;
  parity: number;
  interval_months?: number | null;
  previous_stillbirth: boolean;
  previous_loss: boolean;
  multiple: boolean;
  told_high_bp: boolean;
  anc_visits: number;
}

export interface Driver {
  label: string;
  weight: number;
}

export interface PredictResponse {
  id: number;
  risk: number;
  risk_band: 'low' | 'moderate' | 'high';
  top_drivers: Driver[];
  recommendation: string;
  created_at: string;
  patient_ref?: string;
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
