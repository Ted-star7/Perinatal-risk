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
}
