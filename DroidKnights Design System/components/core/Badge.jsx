import React from 'react';

const tierColors = {
  platinum: 'var(--dk-tier-platinum)',
  gold: 'var(--dk-tier-gold)',
  silver: 'var(--dk-tier-silver)',
  bronze: 'var(--dk-tier-bronze)',
};

/* tone: 'label' (lavender pill, e.g. PRIMARY HERO) | 'solid' (gradient) | tier name */
export function Badge({ children, tone = 'label', style, ...rest }) {
  const isTier = tierColors[tone];
  const s = isTier
    ? { color: 'var(--dk-space)', background: tierColors[tone] }
    : tone === 'solid'
      ? { color: 'var(--dk-on-accent)', background: 'var(--dk-grad-brand)' }
      : { color: 'var(--dk-lavender)', background: 'rgba(177,140,255,.14)', border: '1px solid rgba(177,140,255,.35)' };
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        fontFamily: 'var(--dk-font-display)', fontWeight: 600,
        fontSize: 13, letterSpacing: '.12em', textTransform: 'uppercase',
        padding: '7px 14px', borderRadius: 'var(--dk-radius-chip)',
        ...s, ...style,
      }}
      {...rest}
    >
      {isTier && <span style={{ width: 10, height: 10, borderRadius: '50%', background: 'currentColor', opacity: .55 }} />}
      {children}
    </span>
  );
}
