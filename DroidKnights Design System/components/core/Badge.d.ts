import * as React from 'react';
/** Small uppercase label pill. tone: 'label' (lavender), 'solid' (gradient), or a sponsor tier. */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: 'label' | 'solid' | 'platinum' | 'gold' | 'silver' | 'bronze';
}
export function Badge(props: BadgeProps): JSX.Element;
