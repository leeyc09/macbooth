import React from 'react';

const base = {
  display: 'inline-flex', alignItems: 'center', gap: 10, border: 'none',
  fontFamily: 'var(--dk-font-body)', fontWeight: 700, cursor: 'pointer',
  borderRadius: 'var(--dk-radius-chip)', textDecoration: 'none', whiteSpace: 'nowrap',
  transition: 'transform var(--dk-dur) var(--dk-ease), box-shadow var(--dk-dur) var(--dk-ease), background var(--dk-dur) var(--dk-ease)',
};
const sizes = {
  md: { fontSize: 16, padding: '12px 24px' },
  lg: { fontSize: 20, padding: '18px 38px' },
};
const variants = {
  primary: { background: 'var(--dk-grad-brand)', color: 'var(--dk-on-accent)', boxShadow: 'var(--dk-glow-sm)' },
  secondary: { background: 'var(--dk-glass-bg)', color: 'var(--dk-text)', border: 'var(--dk-glass-border)', backdropFilter: 'var(--dk-blur)' },
  ghost: { background: 'transparent', color: 'var(--dk-text-dim)', border: '1px solid var(--dk-border-strong)' },
};

export function Button({ children, variant = 'primary', size = 'lg', icon, arrow, href, style, ...rest }) {
  const Tag = href ? 'a' : 'button';
  return (
    <Tag href={href} style={{ ...base, ...sizes[size], ...variants[variant], ...style }} {...rest}>
      {icon}
      {children}
      {arrow && <span aria-hidden style={{ fontFamily: 'var(--dk-font-mono)', fontWeight: 400 }}>→</span>}
    </Tag>
  );
}
