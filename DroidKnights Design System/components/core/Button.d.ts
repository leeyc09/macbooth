import * as React from 'react';

/** Primary action control. Gradient primary, glass secondary, outline ghost. */
export interface ButtonProps extends React.HTMLAttributes<HTMLElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'md' | 'lg';
  /** leading icon node */
  icon?: React.ReactNode;
  /** show a trailing → arrow */
  arrow?: boolean;
  /** render as an anchor */
  href?: string;
}
export function Button(props: ButtonProps): JSX.Element;
