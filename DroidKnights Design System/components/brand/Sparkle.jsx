import React from 'react';

/* The DroidKnights 4-point sparkle. Defaults to lavender with a soft glow. */
export function Sparkle({ size = 24, color = 'var(--dk-lavender)', glow = true, style, ...rest }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden
      style={{ filter: glow ? 'drop-shadow(0 2px 10px rgba(123,92,255,.6))' : 'none', ...style }} {...rest}>
      <path d="M50 3C53 33 67 47 97 50C67 53 53 67 50 97C47 67 33 53 3 50C33 47 47 33 50 3Z" fill={color} />
    </svg>
  );
}
