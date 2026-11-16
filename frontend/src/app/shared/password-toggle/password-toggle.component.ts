import { Component, Input, signal } from '@angular/core';

@Component({
  selector: 'app-password-toggle',
  standalone: true,
  template: `
    <button
      type="button"
      [attr.aria-label]="visible() ? 'Hide password' : 'Show password'"
      [attr.aria-pressed]="visible()"
      [attr.aria-controls]="control.id"
      (click)="toggle()"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
        <circle cx="12" cy="12" r="3" />
        @if (visible()) { <path d="m3 3 18 18" /> }
      </svg>
    </button>
  `,
  styles: `
    :host { position: absolute; inset: 0 0 0 auto; width: 48px; }
    button {
      display: grid;
      place-items: center;
      width: 100%;
      height: 100%;
      min-height: 44px;
      border: 0;
      border-radius: 9px;
      background: transparent;
      color: var(--text-secondary);
      padding: 12px;
    }
    button:hover { color: var(--text-primary); }
    svg { width: 22px; height: 22px; }
  `,
})
export class PasswordToggleComponent {
  @Input({ required: true }) control!: HTMLInputElement;
  readonly visible = signal(false);

  toggle(): void {
    this.visible.update((value) => !value);
    this.control.type = this.visible() ? 'text' : 'password';
  }
}
