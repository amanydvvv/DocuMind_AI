export default function BrandIcon({ size = 24, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <defs>
        <linearGradient id="kuery-neon" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#00ffaa" />
          <stop offset="0.5" stopColor="#00d68f" />
          <stop offset="1" stopColor="#00a86b" />
        </linearGradient>
      </defs>
      {/* Neural circuit paths */}
      <path
        d="M12 3L4 8v8l8 5 8-5V8l-8-5z"
        stroke="url(#kuery-neon)"
        strokeWidth="1.5"
        strokeLinejoin="round"
        fill="rgba(0, 214, 143, 0.08)"
      />
      {/* Inner hex node */}
      <path
        d="M12 7L8 9.5v5L12 17l4-2.5v-5L12 7z"
        fill="url(#kuery-neon)"
        opacity="0.7"
      />
      {/* Core pulse */}
      <circle cx="12" cy="12" r="2" fill="#00ffaa" opacity="0.9" />
      <circle cx="12" cy="12" r="1" fill="#ffffff" />
    </svg>
  );
}