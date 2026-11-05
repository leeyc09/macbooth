import * as React from 'react';
/** The DroidKnights 4-point sparkle mark. */
export interface SparkleProps extends React.SVGAttributes<SVGSVGElement> {
  size?: number;
  color?: string;
  glow?: boolean;
}
export function Sparkle(props: SparkleProps): JSX.Element;
