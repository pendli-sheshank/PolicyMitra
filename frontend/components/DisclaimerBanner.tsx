import { AlertCircle } from "lucide-react";

const DEFAULT_TEXT =
  "This information is for general awareness only and is not a substitute for reading your actual policy document or consulting a licensed insurance advisor.";

export default function DisclaimerBanner({ text }: { text?: string }) {
  return (
    <div className="sticky bottom-0 bg-amber-50 dark:bg-amber-950/30 border-t border-amber-200 dark:border-amber-800 px-6 py-4 flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-amber-800 dark:text-amber-200">
        {text || DEFAULT_TEXT}
      </p>
    </div>
  );
}
