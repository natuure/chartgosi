import { ApiRequestError } from "@/lib/api";

export function formatApiError(label: string, error: unknown) {
  if (error instanceof ApiRequestError) {
    return `${label}: HTTP ${error.status}${error.body ? ` ${summarizeBody(error.body)}` : ""}`;
  }
  if (error instanceof Error) {
    return `${label}: ${error.message}`;
  }
  return `${label}: 알 수 없는 오류`;
}

function summarizeBody(body: string) {
  return body.length > 180 ? `${body.slice(0, 180)}...` : body;
}
