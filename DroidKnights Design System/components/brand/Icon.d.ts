import * as React from 'react';
export const ICON_NAMES: string[];
/** Line icon, 24px grid, stroke currentColor. names: booth, session, badge, goods, calendar, ticket, location, clock, mic, code. */
export interface IconProps extends React.SVGAttributes<SVGSVGElement> {
  name: 'booth' | 'session' | 'badge' | 'goods' | 'calendar' | 'ticket' | 'location' | 'clock' | 'mic' | 'code';
  size?: number;
  color?: string;
  strokeWidth?: number;
}
export function Icon(props: IconProps): JSX.Element;
