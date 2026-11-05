import React from 'react';

export const MASCOT_POSES = ['hero', 'wave', 'point', 'cheer', 'laptop', 'flag', 'welcome', 'fly', 'portal', 'back'];

/*
 * Galaxy droid mascot. Transparent PNGs with a soft glow, over dark or light.
 * Pass `pose` + `base` (folder where the mascot PNGs were copied), or an explicit `src`.
 */
export function Mascot({ pose = 'hero', base = 'assets/mascot', src, size = 240, glow = true, alt, style, ...rest }) {
  const url = src || `${base}/${pose}.png`;
  return (
    <img
      src={url}
      alt={alt || `DroidKnights mascot — ${pose}`}
      style={{
        height: size, width: 'auto', objectFit: 'contain',
        filter: glow ? 'var(--dk-glow-mascot)' : 'none',
        ...style,
      }}
      {...rest}
    />
  );
}
