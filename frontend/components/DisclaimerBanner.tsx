const DEFAULT_TEXT =
  "This information is for general awareness only and is not a substitute for reading your actual policy document or consulting a licensed insurance advisor.";

export default function DisclaimerBanner({ text }: { text?: string }) {
  return (
    <div
      style={{
        position: "sticky",
        bottom: 0,
        background: "#fff3cd",
        borderTop: "1px solid #ffe69c",
        padding: "8px 16px",
        fontSize: 13,
        color: "#664d03",
      }}
    >
      {text || DEFAULT_TEXT}
    </div>
  );
}
