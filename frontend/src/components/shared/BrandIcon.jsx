import { useId } from 'react';

export default function BrandIcon({ size = 24, className = '' }) {
  const gradientId = useId();
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
        <linearGradient
          id={gradientId}
          x1="4"
          y1="4"
          x2="20"
          y2="20"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#3b82f6" />
          <stop offset="1" stopColor="#6366f1" />
        </linearGradient>
      </defs>
      <path
        d="M12 2.5l2.1 6.1 6.1 2.1-6.1 2.1L12 19l-2.1-6.2L3.8 10.7l6.1-2.1L12 2.5z"
        fill={`url(#${gradientId})`}
      />
      <path
        d="M18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7.7-2z"
        fill={`url(#${gradientId})`}
        opacity="0.7"
      />
    </svg>
  );
}