import React from 'react';

/* Big gradient figure + label, e.g. 87% · 참가자 만족도. */
export function Stat({ value, suffix, label, style, ...rest }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, ...style }} {...rest}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{
          fontFamily: 'var(--dk-font-body)', fontWeight: 900, fontSize: 64, lineHeight: 1,
          background: 'var(--dk-grad)', WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
        }}>{value}{suffix}</span>
      </div>
      {label && <span style={{ color: 'var(--dk-text-dim)', fontFamily: 'var(--dk-font-body)', fontSize: 18 }}>{label}</span>}
    </div>
  );
}
