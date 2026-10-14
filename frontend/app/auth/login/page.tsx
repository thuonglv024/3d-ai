"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  Sparkles,
  AlertCircle,
  LoaderCircle,
  CheckCircle2,
  ArrowLeft,
  ShieldCheck,
  Activity,
  Layers,
} from "lucide-react";
import { useAuth } from "../../../lib/AuthContext";
import { sanitizeReturnTo, buildAuthUrl } from "../../../lib/authNav";
import "../auth.css";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading, login, refreshUser } = useAuth();

  const rawReturnTo = searchParams?.get("returnTo") || null;
  const returnTo = sanitizeReturnTo(rawReturnTo);
  const intent = searchParams?.get("intent") || null;
  const scanId = searchParams?.get("scan_id") || null;
  const guestToken = searchParams?.get("guest_token") || null;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [statusNotice, setStatusNotice] = useState("");
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  // Register link URL preserving all continuation params
  const registerUrl = buildAuthUrl("register", {
    returnTo: rawReturnTo,
    intent,
    scanId,
    guestToken,
  });

  // Back link URL
  const backUrl = returnTo !== "/account" ? returnTo : "/";

  // If already logged in, handle continuation or redirect
  useEffect(() => {
    if (!authLoading && user) {
      if (intent === "save_scan" && scanId) {
        setStatusNotice("Đang lưu kết quả scan vào hồ sơ hình thể của bạn…");
        setLoading(true);
        fetch("/api/user/scans/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            scan_id: scanId,
            guest_token: guestToken || undefined,
          }),
        })
          .then(async (r) => {
            if (r.ok) {
              const target = returnTo !== "/account" ? returnTo : `/account/body-profile?saved_scan=${encodeURIComponent(scanId)}`;
              router.replace(target);
            } else {
              setErrorMessage("Không thể lưu kết quả scan vào hồ sơ. Vui lòng thử lại sau.");
              setLoading(false);
            }
          })
          .catch(() => {
            setErrorMessage("Lỗi kết nối khi lưu kết quả scan.");
            setLoading(false);
          });
      } else {
        router.replace(returnTo);
      }
    }
  }, [authLoading, user, intent, scanId, guestToken, returnTo, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setErrorMessage("");
    setStatusNotice("");
    setHasSubmitted(true);

    const newErrors: { email?: string; password?: string } = {};
    if (!email.trim()) {
      newErrors.email = "Vui lòng nhập địa chỉ email.";
    }
    if (!password || !password.trim()) {
      newErrors.password = "Vui lòng nhập mật khẩu.";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      const fieldOrder = [
        { key: "email", id: "login-email" },
        { key: "password", id: "login-password" },
      ] as const;
      const firstError = fieldOrder.find((f) => newErrors[f.key]);
      if (firstError) {
        const el = document.getElementById(firstError.id);
        if (el) {
          el.focus();
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
      return;
    }
    setErrors({});

    setLoading(true);

    try {
      const result = await login(email, password);
      if (!result.success) {
        setErrorMessage(result.error || "Email hoặc mật khẩu không đúng.");
        setLoading(false);
        return;
      }

      // Login success: check if there is an intent to save a scan
      if (intent === "save_scan" && scanId) {
        setStatusNotice("Đăng nhập thành công! Đang lưu kết quả scan vào hồ sơ…");
        try {
          const saveRes = await fetch("/api/user/scans/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
              scan_id: scanId,
              guest_token: guestToken || undefined,
            }),
          });

          if (saveRes.ok) {
            setStatusNotice("Đã lưu kết quả scan vào hồ sơ hình thể thành công!");
            await refreshUser();
            setTimeout(() => {
              const target = returnTo !== "/account" ? returnTo : `/account/body-profile?saved_scan=${encodeURIComponent(scanId)}`;
              router.push(target);
            }, 600);
            return;
          } else {
            let detail = "Không thể lưu scan tự động.";
            try {
              const err = await saveRes.json();
              if (err?.detail) detail = err.detail;
            } catch {}
            setStatusNotice(`Đăng nhập thành công, nhưng: ${detail}`);
            setTimeout(() => {
              router.push(returnTo);
            }, 1200);
            return;
          }
        } catch {
          setStatusNotice("Đăng nhập thành công. Vui lòng lưu lại scan từ trang kết quả.");
          setTimeout(() => {
            router.push(returnTo);
          }, 1200);
          return;
        }
      }

      setStatusNotice("Đăng nhập thành công! Đang chuyển hướng…");
      setTimeout(() => {
        router.push(returnTo);
      }, 500);
    } catch {
      setErrorMessage("Đã xảy ra lỗi không mong muốn. Vui lòng thử lại.");
      setLoading(false);
    }
  };

  const isLockoutError =
    errorMessage.toLowerCase().includes("khóa") ||
    errorMessage.toLowerCase().includes("thử quá") ||
    errorMessage.toLowerCase().includes("429") ||
    errorMessage.toLowerCase().includes("lock");

  return (
    <div className="auth-page-wrapper">
      {/* Minimal Top Header */}
      <header className="auth-top-header">
        <Link href="/" className="auth-header-logo" aria-label="MORPH Studio trang chủ">
          MORPH<span>STUDIO</span>
        </Link>
        <Link href={backUrl} className="auth-back-link" aria-label="Quay lại">
          <ArrowLeft size={16} />
          <span>Quay lại</span>
        </Link>
      </header>

      {/* Main Layout */}
      <main className="auth-main-layout">
        <div className="auth-grid-container">
          {/* Left: Atelier Showcase */}
          <aside className="auth-side-panel">
            <div className="auth-side-header">
              <span className="auth-side-badge">
                <Sparkles size={12} />
                MORPH STUDIO · 3D FIT LAB
              </span>
              <h2>Tư vấn kích cỡ trang phục theo vóc dáng</h2>
              <p className="auth-side-lead">
                Công nghệ ước lượng thông số hình thể 3D trực quan hỗ trợ gợi ý kích cỡ trang phục tham khảo, giúp bạn tự tin chọn đồ vừa vặn hơn.
              </p>
            </div>

            <div className="auth-features-list">
              <div className="auth-feature-item">
                <div className="auth-feature-icon">
                  <ShieldCheck size={18} />
                </div>
                <div className="auth-feature-text">
                  <strong>Bảo vệ thông tin cá nhân</strong>
                  <span>Ảnh chụp hai góc chỉ gửi tới máy chủ khi bạn đồng ý để dựng mô hình 3D, không lưu trữ ảnh gốc lâu dài và bạn có thể xóa dữ liệu bất kỳ lúc nào.</span>
                </div>
              </div>

              <div className="auth-feature-item">
                <div className="auth-feature-icon">
                  <Activity size={18} />
                </div>
                <div className="auth-feature-text">
                  <strong>Lưu trữ hồ sơ hình thể tham khảo</strong>
                  <span>Lưu lại kết quả ước lượng số đo vòng ngực, eo, mông để tiện theo dõi và đối chiếu khi mua sắm.</span>
                </div>
              </div>

              <div className="auth-feature-item">
                <div className="auth-feature-icon">
                  <Layers size={18} />
                </div>
                <div className="auth-feature-text">
                  <strong>Gợi ý size tự động</strong>
                  <span>Đối chiếu thông số phom dáng với bảng size của từng thiết kế để đưa ra đề xuất phù hợp.</span>
                </div>
              </div>
            </div>

            <div className="auth-side-footer">
              <span>Hệ thống bảo vệ phiên đăng nhập an toàn và bảo mật thông tin tài khoản của bạn.</span>
            </div>
          </aside>

          {/* Right: Auth Card */}
          <section className="auth-card" aria-label="Form đăng nhập">
            {/* Tabs Switcher */}
            <div className="auth-card-tabs" role="tablist">
              <Link href={buildAuthUrl("login", { returnTo: rawReturnTo, intent, scanId, guestToken })} className="auth-tab-link active" role="tab" aria-selected="true">
                Đăng nhập
              </Link>
              <Link href={registerUrl} className="auth-tab-link" role="tab" aria-selected="false">
                Tạo tài khoản
              </Link>
            </div>

            <div className="auth-card-header">
              <h1 className="auth-card-title">Đăng nhập tài khoản</h1>
              <p className="auth-card-desc">
                Nhập email và mật khẩu của bạn để truy cập tài khoản MORPH Studio.
              </p>
            </div>

            {/* Continuation Banner for saving scan */}
            {intent === "save_scan" && (
              <div className="auth-pending-banner" role="status">
                <Sparkles size={16} className="auth-pending-icon" />
                <span>
                  Đăng nhập để lưu kết quả quét hình thể 3D vừa tạo vào hồ sơ cá nhân của bạn mà không cần quét lại.
                </span>
              </div>
            )}

            {/* Error Banner */}
            {errorMessage && (
              <div className={`auth-error-box ${isLockoutError ? "is-locked" : ""}`} role="alert">
                <AlertCircle size={17} className="auth-error-icon" />
                <div>
                  {isLockoutError && <strong>Tài khoản tạm thời bị giới hạn: </strong>}
                  <span>{errorMessage}</span>
                </div>
              </div>
            )}

            {/* Success Banner */}
            {statusNotice && (
              <div className="auth-success-box" role="status">
                <CheckCircle2 size={17} />
                <span>{statusNotice}</span>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="auth-form" noValidate>
              <div className="auth-field">
                <label htmlFor="login-email" className="auth-label">
                  Địa chỉ Email
                </label>
                <div className="auth-input-wrapper">
                  <Mail size={18} className="auth-input-icon" />
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    required
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => {
                      const val = e.target.value;
                      setEmail(val);
                      if (errors.email && val.trim()) {
                        setErrors((prev) => ({ ...prev, email: undefined }));
                      }
                    }}
                    onBlur={() => {
                      if (hasSubmitted && !email.trim()) {
                        setErrors((prev) => ({ ...prev, email: "Vui lòng nhập địa chỉ email." }));
                      }
                    }}
                    disabled={loading}
                    className={`auth-input ${errors.email ? "is-invalid" : ""}`}
                    aria-invalid={!!errors.email}
                    aria-describedby={errors.email ? "login-email-error" : undefined}
                  />
                </div>
                {errors.email && (
                  <div id="login-email-error" className="auth-field-error" role="alert">
                    <AlertCircle size={13} aria-hidden="true" />
                    <span>{errors.email}</span>
                  </div>
                )}
              </div>

              <div className="auth-field">
                <div className="auth-label-row">
                  <label htmlFor="login-password" className="auth-label">
                    Mật khẩu
                  </label>
                </div>
                <div className="auth-input-wrapper">
                  <Lock size={18} className="auth-input-icon" />
                  <input
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => {
                      const val = e.target.value;
                      setPassword(val);
                      if (errors.password && val.length > 0) {
                        setErrors((prev) => ({ ...prev, password: undefined }));
                      }
                    }}
                    onBlur={() => {
                      if (hasSubmitted && (!password || !password.trim())) {
                        setErrors((prev) => ({ ...prev, password: "Vui lòng nhập mật khẩu." }));
                      }
                    }}
                    disabled={loading}
                    className={`auth-input ${errors.password ? "is-invalid" : ""}`}
                    aria-invalid={!!errors.password}
                    aria-describedby={errors.password ? "login-password-error" : undefined}
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {errors.password && (
                  <div id="login-password-error" className="auth-field-error" role="alert">
                    <AlertCircle size={13} aria-hidden="true" />
                    <span>{errors.password}</span>
                  </div>
                )}
              </div>

              <button type="submit" className="auth-submit-btn" disabled={loading}>
                {loading ? (
                  <>
                    <LoaderCircle size={18} className="auth-spin" />
                    <span>Đang xử lý…</span>
                  </>
                ) : (
                  <span>Đăng nhập ngay</span>
                )}
              </button>
            </form>

            <div className="auth-card-footer">
              <span>Chưa có tài khoản MORPH?</span>
              <Link href={registerUrl} className="auth-switch-link">
                Tạo tài khoản mới
              </Link>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="auth-page-wrapper" style={{ alignItems: "center", justifyContent: "center" }}>
          <LoaderCircle size={36} className="auth-spin" style={{ color: "var(--primary)" }} />
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
