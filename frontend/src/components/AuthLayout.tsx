import React from 'react';
import { ShieldCheck, Sparkles, TrendingUp } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2 bg-[#07131a] text-[#e0e0e1]">
      <div className="relative hidden lg:flex flex-col justify-center overflow-hidden bg-[#091518] p-16">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(210,110,65,.18),transparent_24%),radial-gradient(circle_at_bottom_right,_rgba(99,102,241,.12),transparent_30%)] pointer-events-none" />

        <div className="relative z-10 max-w-[520px] space-y-10">
          <div className="space-y-6">
            <p className="text-sm uppercase tracking-[0.32em] text-[#d26e41]/70">Enterprise AI Sales CRM Assistant</p>
            <h2 className="text-5xl font-semibold tracking-tight text-[#f5f2ef]">Your intelligent sales workspace</h2>
            <p className="max-w-xl text-sm leading-7 text-[#bdb9b3]">
              Manage customers, pipelines, meetings, and follow-ups with AI-powered assistance — all from one secure platform.
            </p>
          </div>

          <div className="grid gap-4">
            <div className="flex items-start gap-3 rounded-[32px] bg-white/5 p-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#d26e41]/15 text-[#d26e41]">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[#f5f2ef]">Smart CRM access</p>
                <p className="text-sm text-[#a6a5a2]">Sign in to retrieve customer data, docs, and sales insights instantly.</p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-[32px] bg-white/5 p-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#d26e41]/15 text-[#d26e41]">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[#f5f2ef]">Secure authentication</p>
                <p className="text-sm text-[#a6a5a2]">JWT-based sessions keep your sales data protected.</p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-[32px] bg-white/5 p-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#d26e41]/15 text-[#d26e41]">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[#f5f2ef]">AI-powered workflows</p>
                <p className="text-sm text-[#a6a5a2]">Automate follow-ups, meeting summaries, and task prioritization.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center bg-[#061017] p-8 lg:p-16">
        <div className="w-full max-w-[460px]">
          {children}
        </div>
      </div>
    </div>
  );
}
