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
        <linearGradient id="solar-amber-core" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FDE68A" />
          <stop offset="0.5" stopColor="#F59E0B" />
          <stop offset="1" stopColor="#B45309" />
        </linearGradient>
      </defs>
      {/* Outer Geometric Diamond Rhombus */}
      <polygon
        points="12,2 21,12 12,22 3,12"
        stroke="url(#solar-amber-core)"
        strokeWidth="1.8"
        strokeLinejoin="round"
        fill="rgba(245, 158, 11, 0.1)"
      />
      {/* Inner Facet Node */}
      <polygon
        points="12,6 18,12 12,18 6,12"
        fill="url(#solar-amber-core)"
        opacity="0.85"
      />
      {/* Core Optical Point */}
      <circle cx="12" cy="12" r="1.5" fill="#FFFFFF" />
    </svg>
  );
}