import { AlertCircle } from "lucide-react";

import { getErrorMessage } from "../api/client";

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) {
    return null;
  }

  return (
    <div className="error-banner" role="alert">
      <AlertCircle aria-hidden="true" />
      <span>{getErrorMessage(error)}</span>
    </div>
  );
}
