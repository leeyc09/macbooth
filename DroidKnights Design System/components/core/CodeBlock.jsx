import React from 'react';

/* Mac-style window card holding mono code. title shows in the titlebar. */
export function CodeBlock({ children, title, style, ...rest }) {
  return (
    <div style={{
      background: 'var(--dk-navy)', border: '1px solid var(--dk-border)',
      borderRadius: 'var(--dk-radius-code)', overflow: 'hidden', ...style,
    }} {...rest}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', borderBottom: '1px solid var(--dk-border)' }}>
        <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#FF5F57' }} />
        <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#FEBC2E' }} />
        <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#28C840' }} />
        {title && <span style={{ marginLeft: 8, fontFamily: 'var(--dk-font-mono)', fontSize: 14, color: 'var(--dk-text-muted)' }}>{title}</span>}
      </div>
      <pre style={{
        margin: 0, padding: '22px 22px', fontFamily: 'var(--dk-font-mono)', fontSize: 16,
        lineHeight: 1.7, color: 'var(--dk-text)', overflowX: 'auto',
      }}>{children}</pre>
    </div>
  );
}
