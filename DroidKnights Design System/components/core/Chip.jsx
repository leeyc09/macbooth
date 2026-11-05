import React from 'react';

export function Chip({ children, active = false, as = 'span', onClick, style, ...rest }) {
  const Tag = as;
  return (
    <Tag
      onClick={onClick}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        fontFamily: 'var(--dk-font-body)', fontWeight: 500, fontSize: 15,
        padding: '10px 20px', borderRadius: 'var(--dk-radius-chip)',
        cursor: onClick ? 'pointer' : 'default',
        color: active ? 'var(--dk-on-accent)' : 'var(--dk-text)',
        background: active ? 'var(--dk-grad-brand)' : 'var(--dk-glass-bg)',
        border: active ? '1px solid transparent' : 'var(--dk-glass-border)',
        backdropFilter: 'var(--dk-blur)',
        boxShadow: active ? 'var(--dk-glow-sm)' : 'none',
        transition: 'all var(--dk-dur) var(--dk-ease)',
        ...style,
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}
