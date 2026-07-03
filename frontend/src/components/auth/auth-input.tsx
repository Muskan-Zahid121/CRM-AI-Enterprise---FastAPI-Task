import { forwardRef } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface AuthInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: LucideIcon;
}

export const AuthInput = forwardRef<HTMLInputElement, AuthInputProps>(
  ({ icon: Icon, className, ...props }, ref) => {
    return (
      <div className="relative">
        {Icon && (
          <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748b]" />
        )}
        <input
          ref={ref}
          className={cn(
            "flex h-11 w-full rounded-xl border border-white/10 bg-[#0b1724] px-4 text-sm text-[#f8fafc] shadow-sm transition-all",
            "placeholder:text-[#64748b] focus:border-[#d26e41]/50 focus:outline-none focus:ring-2 focus:ring-[#d26e41]/20",
            "disabled:cursor-not-allowed disabled:opacity-50",
            Icon && "pl-10",
            className,
          )}
          {...props}
        />
      </div>
    );
  },
);
AuthInput.displayName = "AuthInput";
