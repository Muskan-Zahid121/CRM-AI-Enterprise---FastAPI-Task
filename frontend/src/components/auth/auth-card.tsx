import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <div className="w-full p-2 sm:p-4">
      <div className="mb-6 space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-[#f5f2ef]">{title}</h1>
        <p className="text-sm leading-relaxed text-[#bdb9b3]">{subtitle}</p>
      </div>

      {children}

      {footer && <div className="mt-6 pt-4">{footer}</div>}
    </div>
  );
}
