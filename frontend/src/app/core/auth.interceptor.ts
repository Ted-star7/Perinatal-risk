import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const apiRequest = req.url.startsWith(`${environment.apiBase}/`);
  if (apiRequest && auth.token && !req.headers.has('Authorization')) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${auth.token}` } });
  }
  return next(req).pipe(catchError((error: HttpErrorResponse) => {
    if (apiRequest && error.status === 401 && auth.session()
        && !req.url.endsWith('/login') && !req.url.endsWith('/clinics/register')) {
      auth.expireSession();
    }
    return throwError(() => error);
  }));
};
