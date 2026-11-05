/* @ds-bundle: {"format":4,"namespace":"DroidKnightsDesignSystem_0cd94e","components":[{"name":"Eyebrow","sourcePath":"components/brand/Eyebrow.jsx"},{"name":"ICON_NAMES","sourcePath":"components/brand/Icon.jsx"},{"name":"Icon","sourcePath":"components/brand/Icon.jsx"},{"name":"MASCOT_POSES","sourcePath":"components/brand/Mascot.jsx"},{"name":"Mascot","sourcePath":"components/brand/Mascot.jsx"},{"name":"Sparkle","sourcePath":"components/brand/Sparkle.jsx"},{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"Chip","sourcePath":"components/core/Chip.jsx"},{"name":"CodeBlock","sourcePath":"components/core/CodeBlock.jsx"},{"name":"Stat","sourcePath":"components/core/Stat.jsx"}],"sourceHashes":{"components/brand/Eyebrow.jsx":"3f7a23e8410d","components/brand/Icon.jsx":"13c7bf3d873d","components/brand/Mascot.jsx":"d143920d9974","components/brand/Sparkle.jsx":"56cbfa49380c","components/core/Badge.jsx":"64df19d00361","components/core/Button.jsx":"d22dfdbda657","components/core/Card.jsx":"99787b7eb656","components/core/Chip.jsx":"7ddf132b48b4","components/core/CodeBlock.jsx":"49b3772a0dc5","components/core/Stat.jsx":"e9d01b1bcb6c"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.DroidKnightsDesignSystem_0cd94e = window.DroidKnightsDesignSystem_0cd94e || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/brand/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Line icons: 24px grid, stroke currentColor (defaults to lavender), round caps.
   Matches the DroidKnights conference glyph set. */
const paths = {
  booth: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M4 10 5 5h14l1 5"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M5 10v9h14v-9"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M9 19v-5h6v5"
  })),
  session: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("rect", {
    x: "3",
    y: "4",
    width: "18",
    height: "12",
    rx: "1.5"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 20h8M12 16v4"
  })),
  badge: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("rect", {
    x: "5",
    y: "3",
    width: "14",
    height: "18",
    rx: "2"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "9",
    r: "2.5"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M8 16c.6-2 7.4-2 8 0"
  })),
  goods: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M4 8h16v11H4z"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M4 8 6 4h12l2 4M12 8v11"
  })),
  calendar: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("rect", {
    x: "4",
    y: "5",
    width: "16",
    height: "16",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M4 9h16M8 3v4M16 3v4"
  })),
  ticket: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2 2 2 0 0 0 0 4 2 2 0 0 1-2 2v0H6a2 2 0 0 1-2-2 2 2 0 0 0 0-4z"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M13 6v12",
    strokeDasharray: "2 2"
  })),
  location: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M12 21c4-4 6-7 6-10a6 6 0 1 0-12 0c0 3 2 6 6 10z"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "11",
    r: "2.5"
  })),
  clock: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "8"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 8v4l3 2"
  })),
  mic: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("rect", {
    x: "9",
    y: "3",
    width: "6",
    height: "11",
    rx: "3"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M6 11a6 6 0 0 0 12 0M12 17v4"
  })),
  code: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
    d: "M9 8l-4 4 4 4M15 8l4 4-4 4"
  }))
};
const ICON_NAMES = Object.keys(paths);
function Icon({
  name,
  size = 24,
  color = 'var(--dk-lavender)',
  strokeWidth = 2,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    strokeWidth: strokeWidth,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: style
  }, rest), paths[name] || null);
}
Object.assign(__ds_scope, { ICON_NAMES, Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/Icon.jsx", error: String((e && e.message) || e) }); }

// components/brand/Mascot.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const MASCOT_POSES = ['hero', 'wave', 'point', 'cheer', 'laptop', 'flag', 'welcome', 'fly', 'portal', 'back'];

/*
 * Galaxy droid mascot. Transparent PNGs with a soft glow, over dark or light.
 * Pass `pose` + `base` (folder where the mascot PNGs were copied), or an explicit `src`.
 */
function Mascot({
  pose = 'hero',
  base = 'assets/mascot',
  src,
  size = 240,
  glow = true,
  alt,
  style,
  ...rest
}) {
  const url = src || `${base}/${pose}.png`;
  return /*#__PURE__*/React.createElement("img", _extends({
    src: url,
    alt: alt || `DroidKnights mascot — ${pose}`,
    style: {
      height: size,
      width: 'auto',
      objectFit: 'contain',
      filter: glow ? 'var(--dk-glow-mascot)' : 'none',
      ...style
    }
  }, rest));
}
Object.assign(__ds_scope, { MASCOT_POSES, Mascot });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/Mascot.jsx", error: String((e && e.message) || e) }); }

// components/brand/Sparkle.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* The DroidKnights 4-point sparkle. Defaults to lavender with a soft glow. */
function Sparkle({
  size = 24,
  color = 'var(--dk-lavender)',
  glow = true,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("svg", _extends({
    width: size,
    height: size,
    viewBox: "0 0 100 100",
    "aria-hidden": true,
    style: {
      filter: glow ? 'drop-shadow(0 2px 10px rgba(123,92,255,.6))' : 'none',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("path", {
    d: "M50 3C53 33 67 47 97 50C67 53 53 67 50 97C47 67 33 53 3 50C33 47 47 33 50 3Z",
    fill: color
  }));
}
Object.assign(__ds_scope, { Sparkle });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/Sparkle.jsx", error: String((e && e.message) || e) }); }

// components/brand/Eyebrow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Section eyebrow: sparkle + uppercase tracked label. The DroidKnights section anchor. */
function Eyebrow({
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      fontFamily: 'var(--dk-font-display)',
      fontWeight: 600,
      fontSize: 'var(--dk-fs-eyebrow)',
      letterSpacing: 'var(--dk-tracking-eyebrow)',
      textTransform: 'uppercase',
      color: 'var(--dk-lavender)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Sparkle, {
    size: 16
  }), children);
}
Object.assign(__ds_scope, { Eyebrow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/Eyebrow.jsx", error: String((e && e.message) || e) }); }

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const tierColors = {
  platinum: 'var(--dk-tier-platinum)',
  gold: 'var(--dk-tier-gold)',
  silver: 'var(--dk-tier-silver)',
  bronze: 'var(--dk-tier-bronze)'
};

/* tone: 'label' (lavender pill, e.g. PRIMARY HERO) | 'solid' (gradient) | tier name */
function Badge({
  children,
  tone = 'label',
  style,
  ...rest
}) {
  const isTier = tierColors[tone];
  const s = isTier ? {
    color: 'var(--dk-space)',
    background: tierColors[tone]
  } : tone === 'solid' ? {
    color: 'var(--dk-on-accent)',
    background: 'var(--dk-grad-brand)'
  } : {
    color: 'var(--dk-lavender)',
    background: 'rgba(177,140,255,.14)',
    border: '1px solid rgba(177,140,255,.35)'
  };
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      fontFamily: 'var(--dk-font-display)',
      fontWeight: 600,
      fontSize: 13,
      letterSpacing: '.12em',
      textTransform: 'uppercase',
      padding: '7px 14px',
      borderRadius: 'var(--dk-radius-chip)',
      ...s,
      ...style
    }
  }, rest), isTier && /*#__PURE__*/React.createElement("span", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: 'currentColor',
      opacity: .55
    }
  }), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const base = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 10,
  border: 'none',
  fontFamily: 'var(--dk-font-body)',
  fontWeight: 700,
  cursor: 'pointer',
  borderRadius: 'var(--dk-radius-chip)',
  textDecoration: 'none',
  whiteSpace: 'nowrap',
  transition: 'transform var(--dk-dur) var(--dk-ease), box-shadow var(--dk-dur) var(--dk-ease), background var(--dk-dur) var(--dk-ease)'
};
const sizes = {
  md: {
    fontSize: 16,
    padding: '12px 24px'
  },
  lg: {
    fontSize: 20,
    padding: '18px 38px'
  }
};
const variants = {
  primary: {
    background: 'var(--dk-grad-brand)',
    color: 'var(--dk-on-accent)',
    boxShadow: 'var(--dk-glow-sm)'
  },
  secondary: {
    background: 'var(--dk-glass-bg)',
    color: 'var(--dk-text)',
    border: 'var(--dk-glass-border)',
    backdropFilter: 'var(--dk-blur)'
  },
  ghost: {
    background: 'transparent',
    color: 'var(--dk-text-dim)',
    border: '1px solid var(--dk-border-strong)'
  }
};
function Button({
  children,
  variant = 'primary',
  size = 'lg',
  icon,
  arrow,
  href,
  style,
  ...rest
}) {
  const Tag = href ? 'a' : 'button';
  return /*#__PURE__*/React.createElement(Tag, _extends({
    href: href,
    style: {
      ...base,
      ...sizes[size],
      ...variants[variant],
      ...style
    }
  }, rest), icon, children, arrow && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": true,
    style: {
      fontFamily: 'var(--dk-font-mono)',
      fontWeight: 400
    }
  }, "\u2192"));
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Navy surface card, 22px radius. glow adds the brand shadow; padded=false for media cards. */
function Card({
  children,
  glow = false,
  padded = true,
  as = 'div',
  style,
  ...rest
}) {
  const Tag = as;
  return /*#__PURE__*/React.createElement(Tag, _extends({
    style: {
      background: 'var(--dk-surface)',
      border: '1px solid var(--dk-border)',
      borderRadius: 'var(--dk-radius-card)',
      boxShadow: glow ? 'var(--dk-glow)' : 'var(--dk-shadow-card)',
      padding: padded ? 32 : 0,
      overflow: 'hidden',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/Chip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Chip({
  children,
  active = false,
  as = 'span',
  onClick,
  style,
  ...rest
}) {
  const Tag = as;
  return /*#__PURE__*/React.createElement(Tag, _extends({
    onClick: onClick,
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      fontFamily: 'var(--dk-font-body)',
      fontWeight: 500,
      fontSize: 15,
      padding: '10px 20px',
      borderRadius: 'var(--dk-radius-chip)',
      cursor: onClick ? 'pointer' : 'default',
      color: active ? 'var(--dk-on-accent)' : 'var(--dk-text)',
      background: active ? 'var(--dk-grad-brand)' : 'var(--dk-glass-bg)',
      border: active ? '1px solid transparent' : 'var(--dk-glass-border)',
      backdropFilter: 'var(--dk-blur)',
      boxShadow: active ? 'var(--dk-glow-sm)' : 'none',
      transition: 'all var(--dk-dur) var(--dk-ease)',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Chip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Chip.jsx", error: String((e && e.message) || e) }); }

// components/core/CodeBlock.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Mac-style window card holding mono code. title shows in the titlebar. */
function CodeBlock({
  children,
  title,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: 'var(--dk-navy)',
      border: '1px solid var(--dk-border)',
      borderRadius: 'var(--dk-radius-code)',
      overflow: 'hidden',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '14px 18px',
      borderBottom: '1px solid var(--dk-border)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 12,
      height: 12,
      borderRadius: '50%',
      background: '#FF5F57'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 12,
      height: 12,
      borderRadius: '50%',
      background: '#FEBC2E'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 12,
      height: 12,
      borderRadius: '50%',
      background: '#28C840'
    }
  }), title && /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 8,
      fontFamily: 'var(--dk-font-mono)',
      fontSize: 14,
      color: 'var(--dk-text-muted)'
    }
  }, title)), /*#__PURE__*/React.createElement("pre", {
    style: {
      margin: 0,
      padding: '22px 22px',
      fontFamily: 'var(--dk-font-mono)',
      fontSize: 16,
      lineHeight: 1.7,
      color: 'var(--dk-text)',
      overflowX: 'auto'
    }
  }, children));
}
Object.assign(__ds_scope, { CodeBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/CodeBlock.jsx", error: String((e && e.message) || e) }); }

// components/core/Stat.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Big gradient figure + label, e.g. 87% · 참가자 만족도. */
function Stat({
  value,
  suffix,
  label,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--dk-font-body)',
      fontWeight: 900,
      fontSize: 64,
      lineHeight: 1,
      background: 'var(--dk-grad)',
      WebkitBackgroundClip: 'text',
      backgroundClip: 'text',
      color: 'transparent'
    }
  }, value, suffix)), label && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--dk-text-dim)',
      fontFamily: 'var(--dk-font-body)',
      fontSize: 18
    }
  }, label));
}
Object.assign(__ds_scope, { Stat });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Stat.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Eyebrow = __ds_scope.Eyebrow;

__ds_ns.ICON_NAMES = __ds_scope.ICON_NAMES;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.MASCOT_POSES = __ds_scope.MASCOT_POSES;

__ds_ns.Mascot = __ds_scope.Mascot;

__ds_ns.Sparkle = __ds_scope.Sparkle;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Chip = __ds_scope.Chip;

__ds_ns.CodeBlock = __ds_scope.CodeBlock;

__ds_ns.Stat = __ds_scope.Stat;

})();
