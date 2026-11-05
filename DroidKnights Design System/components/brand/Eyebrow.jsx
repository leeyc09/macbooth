import React from 'react';
import { Sparkle } from './Sparkle.jsx';

/* Section eyebrow: sparkle + uppercase tracked label. The DroidKnights section anchor. */
export function Eyebrow({ children, style, ...rest }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 10,
      fontFamily: 'var(--dk-font-display)', fontWeight: 600,
      fontSize: 'var(--dk-fs-eyebrow)', letterSpacing: 'var(--dk-tracking-eyebrow)',
      textTransform: 'uppercase', color: 'var(--dk-lavender)', ...style,
    }} {...rest}>
      <Sparkle size={16} />
      {children}
    </div>
  );
}
