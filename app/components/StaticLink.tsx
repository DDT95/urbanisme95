import type { AnchorHTMLAttributes, ReactNode } from "react";

export default function StaticLink({ href, children, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) {
  const basePath = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
  const resolvedHref = href.startsWith("/") ? `${basePath}${href}` : href;
  return <a href={resolvedHref} {...props}>{children}</a>;
}
