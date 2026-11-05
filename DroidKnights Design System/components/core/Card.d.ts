import * as React from 'react';
/** Navy surface container, 22px radius. */
export interface CardProps extends React.HTMLAttributes<HTMLElement> {
  /** use the brand glow shadow instead of the flat card shadow */
  glow?: boolean;
  /** default 32px internal padding; false for media/full-bleed cards */
  padded?: boolean;
  as?: any;
}
export function Card(props: CardProps): JSX.Element;
