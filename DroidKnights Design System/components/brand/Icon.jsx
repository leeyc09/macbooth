import React from 'react';

/* Line icons: 24px grid, stroke currentColor (defaults to lavender), round caps.
   Matches the DroidKnights conference glyph set. */
const paths = {
  booth: <><path d="M4 10 5 5h14l1 5" /><path d="M5 10v9h14v-9" /><path d="M9 19v-5h6v5" /></>,
  session: <><rect x="3" y="4" width="18" height="12" rx="1.5" /><path d="M8 20h8M12 16v4" /></>,
  badge: <><rect x="5" y="3" width="14" height="18" rx="2" /><circle cx="12" cy="9" r="2.5" /><path d="M8 16c.6-2 7.4-2 8 0" /></>,
  goods: <><path d="M4 8h16v11H4z" /><path d="M4 8 6 4h12l2 4M12 8v11" /></>,
  calendar: <><rect x="4" y="5" width="16" height="16" rx="2" /><path d="M4 9h16M8 3v4M16 3v4" /></>,
  ticket: <><path d="M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2 2 2 0 0 0 0 4 2 2 0 0 1-2 2v0H6a2 2 0 0 1-2-2 2 2 0 0 0 0-4z" /><path d="M13 6v12" strokeDasharray="2 2" /></>,
  location: <><path d="M12 21c4-4 6-7 6-10a6 6 0 1 0-12 0c0 3 2 6 6 10z" /><circle cx="12" cy="11" r="2.5" /></>,
  clock: <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></>,
  mic: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M6 11a6 6 0 0 0 12 0M12 17v4" /></>,
  code: <><path d="M9 8l-4 4 4 4M15 8l4 4-4 4" /></>,
};

export const ICON_NAMES = Object.keys(paths);

export function Icon({ name, size = 24, color = 'var(--dk-lavender)', strokeWidth = 2, style, ...rest }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
      style={style} {...rest}>
      {paths[name] || null}
    </svg>
  );
}
