import type { LabelHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface AuthLabelProps extends LabelHTMLAttributes<HTMLLabelElement> {}

export function AuthLabel({ className, ...props }: AuthLabelProps) {
  return (
    <label
      className={cn(
        "text-xs font-medium tracking-wide text-[#94a3b8]",
        className,
      )}
      {...props}
    />
  );
}
