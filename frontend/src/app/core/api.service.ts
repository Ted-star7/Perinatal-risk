import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, timeout } from 'rxjs';
import {
  BirthOutcome,
  BirthOutcomeInput,
  LoginBody,
  PredictRequest,
  PredictResponse,
  RegisterBody,
  Session,
  AssessmentResult,
} from './models';
import { environment } from '../../environments/environment';

export const API_BASE = environment.apiBase;

export interface ModelRelease {
  cohort: string;
  available: boolean;
  serving?: boolean;
  prediction_context?: string;
  algorithm?: string;
  model_id?: string;
  created_at?: string;
  features?: string[];
  evaluation?: {
    selection?: string;
    test: {
      mean_score: number; event_rate: number; brier_score: number;
      pr_auc?: number; roc_auc?: number; rows?: number; events?: number;
    };
    country_metrics?: Record<string, { unweighted: { roc_auc: number; pr_auc: number } }>;
  };
}

export interface ModelMetricResponse {
  cv_pr_auc?: number;
  cv_pr_auc_std?: number;
  cases_caught?: number;
  evaluation_id?: string;
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

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  register(body: RegisterBody): Observable<Session> {
    return this.http.post<Session>(`${API_BASE}/clinics/register`, body);
  }

  login(body: LoginBody): Observable<Session> {
    return this.http.post<Session>(`${API_BASE}/login`, body);
  }

  predict(body: PredictRequest): Observable<PredictResponse> {
    return this.http.post<PredictResponse>(`${API_BASE}/predict`, body).pipe(timeout(90000));
  }

  assess(body: PredictRequest): Observable<AssessmentResult> {
    return this.http.post<AssessmentResult>(`${API_BASE}/assess`, body).pipe(timeout(90000));
  }

  history(search = '', before?: number): Observable<PredictResponse[]> {
    let params = new HttpParams().set('search', search).set('limit', 25);
    if (before) params = params.set('before', before);
    return this.http.get<PredictResponse[]>(`${API_BASE}/history`, { params });
  }

  saveOutcome(id: number, body: BirthOutcomeInput): Observable<BirthOutcome> {
    return this.http.post<BirthOutcome>(`${API_BASE}/predictions/${id}/outcomes`, body);
  }

  outcomeHistory(id: number): Observable<BirthOutcome[]> {
    return this.http.get<BirthOutcome[]>(`${API_BASE}/predictions/${id}/outcomes`);
  }

  session(): Observable<{ is_owner: boolean }> {
    return this.http.get<{ is_owner: boolean }>(`${API_BASE}/session`);
  }

  logout(token: string) {
    return this.http.post(`${API_BASE}/logout`, {}, { headers: { Authorization: `Bearer ${token}` } });
  }

  join(body: { token: string; doctor_name: string; password: string }): Observable<Session> {
    return this.http.post<Session>(`${API_BASE}/clinics/join`, body);
  }

  invite(email: string) {
    return this.http.post<{ token: string; email: string }>(`${API_BASE}/clinics/invitations`, { email });
  }

  changePassword(current_password: string, new_password: string): Observable<Session> {
    return this.http.post<Session>(`${API_BASE}/password`, { current_password, new_password });
  }

  releases(): Observable<ModelRelease[]> {
    return this.http.get<ModelRelease[]>(`${API_BASE}/model-releases`);
  }

  metrics(): Observable<ModelMetricResponse[]> {
    return this.http.get<ModelMetricResponse[]>(`${API_BASE}/evaluation-metrics`);
  }

}
