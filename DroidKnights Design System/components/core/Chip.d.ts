import * as React from 'react';
/** Glass pill for filters / nav / tags. active fills with the brand gradient. */
export interface ChipProps extends React.HTMLAttributes<HTMLElement> {
  active?: boolean;
  as?: any;
}
export function Chip(props: ChipProps): JSX.Element;
