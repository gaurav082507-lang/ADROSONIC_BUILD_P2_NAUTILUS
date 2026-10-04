/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_USE_MOCKS?: string;
  readonly VITE_DEMO_INVESTIGATOR_EMAIL?: string;
  readonly VITE_DEMO_CLAIMANT_EMAIL?: string;
  readonly VITE_DEMO_PASSWORD?: string;
  readonly VITE_FEATURES?: string;
  readonly BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
