import * as React from 'react';
/** Big gradient figure with a caption, for metrics. */
export interface StatProps extends React.HTMLAttributes<HTMLDivElement> {
  value: React.ReactNode;
  suffix?: React.ReactNode;
  label?: React.ReactNode;
}
export function Stat(props: StatProps): JSX.Element;
