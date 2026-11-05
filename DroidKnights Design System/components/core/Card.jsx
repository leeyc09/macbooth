import React from 'react';

/* Navy surface card, 22px radius. glow adds the brand shadow; padded=false for media cards. */
export function Card({ children, glow = false, padded = true, as = 'div', style, ...rest }) {
  const Tag = as;
  return (
    <Tag
      style={{
        background: 'var(--dk-surface)',
        border: '1px solid var(--dk-border)',
        borderRadius: 'var(--dk-radius-card)',
        boxShadow: glow ? 'var(--dk-glow)' : 'var(--dk-shadow-card)',
        padding: padded ? 32 : 0,
        overflow: 'hidden',
        ...style,
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}
