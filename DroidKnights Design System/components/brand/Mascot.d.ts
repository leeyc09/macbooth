import * as React from 'react';
export const MASCOT_POSES: string[];
/** Galaxy droid mascot (transparent PNG + glow). */
export interface MascotProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  pose?: 'hero' | 'wave' | 'point' | 'cheer' | 'laptop' | 'flag' | 'welcome' | 'fly' | 'portal' | 'back';
  /** folder the mascot PNGs were copied to (default 'assets/mascot') */
  base?: string;
  src?: string;
  size?: number;
  glow?: boolean;
}
export function Mascot(props: MascotProps): JSX.Element;
