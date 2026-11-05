import * as React from 'react';
/** Mac-window code card with mono content. */
export interface CodeBlockProps extends React.HTMLAttributes<HTMLDivElement> {
  /** filename shown in the titlebar */
  title?: string;
}
export function CodeBlock(props: CodeBlockProps): JSX.Element;
