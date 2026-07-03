import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mail } from "lucide-react";
import { authApi } from "@/api/auth";
import AuthLayout from "@/components/AuthLayout";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthInput } from "@/components/auth/auth-input";
import { AuthLabel } from "@/components/auth/auth-label";
import { AuthSubmitButton } from "@/components/auth/auth-submit-button";
import { AuthFieldError } from "@/components/auth/auth-field-error";
import { AuthAlert } from "@/components/auth/auth-alert";
import { PasswordField } from "@/components/auth/password-field";

interface Props {
  onSuccess: () => void;
  onGoSignup: () => void;
  signupMessage?: string;
}

interface FormData {
  email: string;
  password: string;
}

interface FormErrors {
  email?: string;
  password?: string;
}

export default function LoginPage({ onSuccess, onGoSignup, signupMessage }: Props) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<FormData>({ email: "", password: "" });
  const [errors, setErrors] = useState<FormErrors>({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

  const validate = (): FormErrors => {
    const next: FormErrors = {};
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!formData.email) next.email = "Email is required";
    else if (!emailRegex.test(formData.email)) next.email = "Please enter a valid email address";
    if (!formData.password) next.password = "Password is required";
    return next;
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError("");
    const nextErrors = validate();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      await authApi.login(formData.email, formData.password);
      onSuccess();
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <AuthCard
        title="Welcome back"
        subtitle="Sign in to your Enterprise AI Sales CRM workspace"
        footer={
          <div className="flex justify-center">
            <p className="text-sm text-[#94a3b8]">
              Don&apos;t have an account?{" "}
              <button
                type="button"
                onClick={onGoSignup}
                className="font-medium text-[#d26e41] hover:text-[#ff8c63]"
              >
                Sign up
              </button>
            </p>
          </div>
        }
      >
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {signupMessage && <AuthAlert message={signupMessage} variant="success" />}
          {apiError && <AuthAlert message={apiError} variant="error" />}

          <div className="space-y-2">
            <AuthLabel htmlFor="email">Email</AuthLabel>
            <AuthInput
              id="email"
              icon={Mail}
              type="email"
              placeholder="Enter your email"
              value={formData.email}
              onChange={(e) => {
                setFormData({ ...formData, email: e.target.value });
                if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }));
              }}
              autoComplete="email"
              aria-invalid={Boolean(errors.email)}
              className={errors.email ? "border-red-400/60 focus:border-red-400 focus:ring-red-400/20" : undefined}
            />
            <AuthFieldError error={errors.email} />
          </div>

          <PasswordField
            id="password"
            label="Password"
            value={formData.password}
            onChange={(password) => {
              setFormData({ ...formData, password });
              if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }));
            }}
            error={errors.password}
          />

          <AuthSubmitButton loading={loading} loadingLabel="Signing in..." label="Sign in" />
        </form>
      </AuthCard>
    </AuthLayout>
  );
}
