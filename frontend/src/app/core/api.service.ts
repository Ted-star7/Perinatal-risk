import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  LoginBody,
  PredictRequest,
  PredictResponse,
  RegisterBody,
  Session,
} from './models';
import { environment } from '../../environments/environment';

export const API_BASE = environment.apiBase;

export interface ModelMetricResponse {
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
    return this.http.post<PredictResponse>(`${API_BASE}/predict`, body);
  }

  history(): Observable<PredictResponse[]> {
    return this.http.get<PredictResponse[]>(`${API_BASE}/history`);
  }

  metrics(): Observable<ModelMetricResponse[]> {
    return this.http.get<ModelMetricResponse[]>(`${API_BASE}/metrics`);
  }

}
