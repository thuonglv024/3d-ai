"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  User as UserIcon,
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

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading, register, refreshUser } = useAuth();

  const rawReturnTo = searchParams?.get("returnTo") || null;
  const returnTo = sanitizeReturnTo(rawReturnTo);
  const intent = searchParams?.get("intent") || null;
  const scanId = searchParams?.get("scan_id") || null;
  const guestToken = searchParams?.get("guest_token") || null;

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [statusNotice, setStatusNotice] = useState("");
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [errors, setErrors] = useState<{
    displayName?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  // Login link URL preserving all continuation params
  const loginUrl = buildAuthUrl("login", {
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

    const newErrors: {
      displayName?: string;
      email?: string;
      password?: string;
      confirmPassword?: string;
    } = {};

    if (!displayName.trim()) {
      newErrors.displayName = "Vui lòng nhập tên hiển thị.";
    }

    if (!email.trim()) {
      newErrors.email = "Vui lòng nhập địa chỉ email.";
    }

    if (!password || !password.trim()) {
      newErrors.password = "Vui lòng nhập mật khẩu.";
    }

    if (!confirmPassword || !confirmPassword.trim()) {
      newErrors.confirmPassword = "Vui lòng xác nhận mật khẩu.";
    } else if (password && confirmPassword && password !== confirmPassword) {
      newErrors.confirmPassword = "Mật khẩu xác nhận không khớp.";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      const fieldOrder = [
        { key: "displayName", id: "register-displayName" },
        { key: "email", id: "register-email" },
        { key: "password", id: "register-password" },
        { key: "confirmPassword", id: "register-confirmPassword" },
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
      const result = await register(email, password, displayName);
      if (!result.success) {
        setErrorMessage(result.error || "Không thể tạo tài khoản. Vui lòng thử lại.");
        setLoading(false);
        return;
      }

      // Registration success: check if there is an intent to save a scan
      if (intent === "save_scan" && scanId) {
        setStatusNotice("Tạo tài khoản thành công! Đang lưu kết quả scan vào hồ sơ…");
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
            setStatusNotice(`Đăng ký thành công, nhưng: ${detail}`);
            setTimeout(() => {
              router.push(returnTo);
            }, 1200);
            return;
          }
        } catch {
          setStatusNotice("Đăng ký thành công. Vui lòng lưu lại scan từ trang kết quả.");
          setTimeout(() => {
            router.push(returnTo);
          }, 1200);
          return;
        }
      }

      setStatusNotice("Tạo tài khoản thành công! Đang chuyển hướng…");
      setTimeout(() => {
        router.push(returnTo);
      }, 500);
    } catch {
      setErrorMessage("Đã xảy ra lỗi không mong muốn. Vui lòng thử lại.");
      setLoading(false);
    }
  };

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
          <section className="auth-card" aria-label="Form đăng ký tài khoản">
            {/* Tabs Switcher */}
            <div className="auth-card-tabs" role="tablist">
              <Link href={loginUrl} className="auth-tab-link" role="tab" aria-selected="false">
                Đăng nhập
              </Link>
              <Link href={buildAuthUrl("register", { returnTo: rawReturnTo, intent, scanId, guestToken })} className="auth-tab-link active" role="tab" aria-selected="true">
                Tạo tài khoản
              </Link>
            </div>

            <div className="auth-card-header">
              <h1 className="auth-card-title">Tạo tài khoản mới</h1>
              <p className="auth-card-desc">
                Đăng ký thành viên MORPH Studio để lưu trữ số đo hình thể và nhận tư vấn kích cỡ.
              </p>
            </div>

            {/* Continuation Banner for saving scan */}
            {intent === "save_scan" && (
              <div className="auth-pending-banner" role="status">
                <Sparkles size={16} className="auth-pending-icon" />
                <span>
                  Đăng ký tài khoản để tự động lưu kết quả quét hình thể 3D vừa tạo vào hồ sơ cá nhân của bạn.
                </span>
              </div>
            )}

            {/* Error Banner */}
            {errorMessage && (
              <div className="auth-error-box" role="alert">
                <AlertCircle size={17} className="auth-error-icon" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Success Banner */}
            {statusNotice && (
              <div className="auth-success-box" role="status">
                <CheckCircle2 size={17} />
                <span>{statusNotice}</span>
              </div>
            )}

            {/* Register Form */}
            <form onSubmit={handleSubmit} className="auth-form" noValidate>
              <div className="auth-field">
                <label htmlFor="register-displayName" className="auth-label">
                  Tên hiển thị
                </label>
                <div className="auth-input-wrapper">
                  <UserIcon size={18} className="auth-input-icon" />
                  <input
                    id="register-displayName"
                    type="text"
                    autoComplete="name"
                    required
                    placeholder="Ví dụ: Hoàng Nam"
                    value={displayName}
                    onChange={(e) => {
                      const val = e.target.value;
                      setDisplayName(val);
                      if (errors.displayName && val.trim()) {
                        setErrors((prev) => ({ ...prev, displayName: undefined }));
                      }
                    }}
                    onBlur={() => {
                      if (hasSubmitted && !displayName.trim()) {
                        setErrors((prev) => ({ ...prev, displayName: "Vui lòng nhập tên hiển thị." }));
                      }
                    }}
                    disabled={loading}
                    className={`auth-input ${errors.displayName ? "is-invalid" : ""}`}
                    aria-invalid={!!errors.displayName}
                    aria-describedby={errors.displayName ? "register-displayName-error" : undefined}
                  />
                </div>
                {errors.displayName && (
                  <div id="register-displayName-error" className="auth-field-error" role="alert">
                    <AlertCircle size={13} aria-hidden="true" />
                    <span>{errors.displayName}</span>
                  </div>
                )}
              </div>

              <div className="auth-field">
                <label htmlFor="register-email" className="auth-label">
                  Địa chỉ Email
                </label>
                <div className="auth-input-wrapper">
                  <Mail size={18} className="auth-input-icon" />
                  <input
                    id="register-email"
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
                    aria-describedby={errors.email ? "register-email-error" : undefined}
                  />
                </div>
                {errors.email && (
                  <div id="register-email-error" className="auth-field-error" role="alert">
                    <AlertCircle size={13} aria-hidden="true" />
                    <span>{errors.email}</span>
                  </div>
                )}
              </div>

              <div className="auth-field">
                <div className="auth-label-row">
                  <label htmlFor="register-password" className="auth-label">
                    Mật khẩu
                  </label>
                </div>
                <div className="auth-input-wrapper">
                  <Lock size={18} className="auth-input-icon" />
                  <input
                    id="register-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    placeholder="Nhập mật khẩu"
                    value={password}
                    onChange={(e) => {
                      const val = e.target.value;
                      setPassword(val);
                      if (errors.password && val.length > 0) {
                        setErrors((prev) => ({ ...prev, password: undefined }));
                      }
                      if (errors.confirmPassword && confirmPassword && val === confirmPassword) {
                        setErrors((prev) => ({ ...prev, confirmPassword: undefined }));
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
                    aria-describedby={errors.password ? "register-password-error" : undefined}
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
                  <div id="register-password-error" className="auth-field-error" role="alert">
                    <AlertCircle size={13} aria-hidden="true" />
                    <span>{errors.password}</span>
                  </div>
                )}
              </div>

              <div className="auth-field">
                <label htmlFor="register-confirmPassword" className="auth-label">
                  Xác nhận mật khẩu
                </label>
                <div className="auth-input-wrapper">
                  <Lock size={18} className="auth-input-icon" />
                  <input
                    id="register-confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    placeholder="Nhập lại mật khẩu"
                    value={confirmPassword}
                    onChange={(e) => {
                      const val = e.target.value;
                      setConfirmPassword(val);
                      if (errors.confirmPassword) {
                        if (val && (!password || val === password)) {
                          setErrors((prev) => ({ ...prev, confirmPassword: undefined }));
                        }
                      }
                    }}
                    onBlur={() => {
                      if (hasSubmitted) {
                        if (!confirmPassword || !confirmPassword.trim()) {
                          setErrors((prev) => ({ ...prev, confirmPassword: "Vui lòng xác nhận mật khẩu." }));
                        } else if (password && confirmPassword !== password) {
                          setErrors((prev) => ({ ...prev, confirmPassword: "Mật khẩu xác nhận không khớp." }));
                        }
                      }
                    }}
                    disabled={loading}
                    className={`auth-input ${errors.confirmPassword ? "is-invalid" : ""}`}
                    aria-invalid={!!errors.confirmPassword}
                    aria-describedby={errors.confirmPassword ? "register-confirmPassword-error" : undefined}
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <div id="register-confirmPassword-error" className="auth-field-error" role="alert">
                    <AlertCircle size={13} aria-hidden="true" />
                    <span>{errors.confirmPassword}</span>
                  </div>
                )}
              </div>

              <button type="submit" className="auth-submit-btn" disabled={loading}>
                {loading ? (
                  <>
                    <LoaderCircle size={18} className="auth-spin" />
                    <span>Đang tạo tài khoản…</span>
                  </>
                ) : (
                  <span>Đăng ký tài khoản</span>
                )}
              </button>
            </form>

            <div className="auth-card-footer">
              <span>Đã có tài khoản MORPH?</span>
              <Link href={loginUrl} className="auth-switch-link">
                Đăng nhập tại đây
              </Link>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="auth-page-wrapper" style={{ alignItems: "center", justifyContent: "center" }}>
          <LoaderCircle size={36} className="auth-spin" style={{ color: "var(--primary)" }} />
        </div>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
