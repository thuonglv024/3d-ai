"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  User as UserIcon,
  Activity,
  Calendar,
  Settings,
  ShieldCheck,
  Edit3,
  Check,
  X,
  ArrowRight,
  LogOut,
  Camera,
  LoaderCircle,
  Clock,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import Header from "../../components/shop/Header";
import Footer from "../../components/shop/Footer";
import CartDrawer from "../../components/shop/CartDrawer";
import WishlistDrawer from "../../components/shop/WishlistDrawer";
import { useAuth } from "../../lib/AuthContext";
import {
  fetchUserScans,
  formatScanDateTime,
  type BodyScanSummary,
} from "../../lib/userScansApi";

export default function AccountOverviewPage() {
  const { user, loading: authLoading, updateProfile, logout } = useAuth();

  const [editingName, setEditingName] = useState(false);
  const [displayNameInput, setDisplayNameInput] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [nameError, setNameError] = useState("");

  const [savingToggle, setSavingToggle] = useState(false);
  const [toggleSuccessToast, setToggleSuccessToast] = useState("");

  const [totalScans, setTotalScans] = useState<number | null>(null);
  const [latestScan, setLatestScan] = useState<BodyScanSummary | null>(null);
  const [loadingScans, setLoadingScans] = useState(false);

  // Sync display name input when user data changes
  useEffect(() => {
    if (user?.display_name) {
      setDisplayNameInput(user.display_name);
    }
  }, [user?.display_name]);

  // Fetch scans count and latest scan if logged in
  useEffect(() => {
    if (!user) {
      setTotalScans(null);
      setLatestScan(null);
      return;
    }

    let aborted = false;
    setLoadingScans(true);

    fetchUserScans({ page: 1, limit: 1 })
      .then((res) => {
        if (!aborted) {
          setTotalScans(res.total);
          if (res.items && res.items.length > 0) {
            setLatestScan(res.items[0]);
          } else {
            setLatestScan(null);
          }
          setLoadingScans(false);
        }
      })
      .catch((err) => {
        if (!aborted) {
          console.warn("Could not load user scans summary:", err);
          setLoadingScans(false);
        }
      });

    return () => {
      aborted = true;
    };
  }, [user]);

  // Handle display name update
  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayNameInput.trim()) {
      setNameError("Tên hiển thị không được để trống.");
      return;
    }

    setSavingName(true);
    setNameError("");
    try {
      const ok = await updateProfile({ display_name: displayNameInput.trim() });
      if (ok) {
        setEditingName(false);
      } else {
        setNameError("Không thể lưu tên. Vui lòng thử lại.");
      }
    } catch {
      setNameError("Lỗi kết nối khi cập nhật tên.");
    } finally {
      setSavingName(false);
    }
  };

  // Handle auto-save toggle
  const handleToggleAutoSave = async () => {
    if (!user || savingToggle) return;
    const nextVal = !user.auto_save_scans;
    setSavingToggle(true);
    try {
      const ok = await updateProfile({ auto_save_scans: nextVal });
      if (ok) {
        setToggleSuccessToast(
          nextVal ? "Đã bật tự động lưu kết quả scan." : "Đã tắt tự động lưu kết quả scan."
        );
        setTimeout(() => setToggleSuccessToast(""), 3500);
      }
    } catch {
      // Revert if error
    } finally {
      setSavingToggle(false);
    }
  };

  return (
    <div className="account-page-layout">
      <Header />
      <CartDrawer />
      <WishlistDrawer />

      <main className="account-main-content">
        {/* Breadcrumb Navigation */}
        <nav className="account-breadcrumbs" aria-label="Điều hướng đường dẫn">
          <Link href="/">Trang chủ</Link>
          <span className="bc-separator">/</span>
          <span className="bc-current">Tài khoản cá nhân</span>
        </nav>

        {/* Auth Loading Spinner */}
        {authLoading && (
          <div className="account-auth-guard-box">
            <LoaderCircle size={44} className="spin-gold" />
            <p style={{ marginTop: 16 }}>Đang xác thực thông tin tài khoản…</p>
          </div>
        )}

        {/* Unauthenticated State */}
        {!authLoading && !user && (
          <div className="account-auth-guard-box">
            <div className="guard-icon-circle">
              <UserIcon size={32} />
            </div>
            <h2>Tài khoản MORPH Studio</h2>
            <p>
              Đăng nhập hoặc đăng ký tài khoản để lưu trữ hồ sơ hình thể cá nhân, theo dõi xu hướng
              thay đổi số đo theo thời gian và đối chiếu các lần quét 3D qua camera.
            </p>
            <div className="guard-actions-row">
              <Link href="/auth/login?returnTo=/account" className="btn-gold-primary">
                Đăng nhập / Đăng ký
              </Link>
              <Link href="/scan" className="btn-gold-secondary">
                <Camera size={16} /> Thử quét hình thể ngay
              </Link>
            </div>
          </div>
        )}

        {/* Authenticated Account Overview */}
        {!authLoading && user && (
          <>
            {/* Header Title Area */}
            <div className="account-header-area">
              <div className="account-header-title-box">
                <h1>Hồ sơ & Tài khoản</h1>
                <p className="account-header-subtitle">
                  Quản lý thông tin cá nhân và thiết lập lưu trữ số đo hình thể 3D tại MORPH Studio.
                </p>
              </div>

              <div className="account-header-actions">
                <Link href="/scan" className="btn-gold-primary">
                  <Camera size={16} /> Quét hình thể mới
                </Link>
                <button
                  type="button"
                  className="btn-danger-outline"
                  onClick={() => logout()}
                  title="Đăng xuất khỏi thiết bị này"
                >
                  <LogOut size={15} /> Đăng xuất
                </button>
              </div>
            </div>

            {/* Quick Feature Banner leading to Body Profile */}
            <Link href="/account/body-profile" className="body-profile-nav-card">
              <div className="nav-card-left">
                <div className="nav-card-icon-box">
                  <Activity size={32} />
                </div>
                <div className="nav-card-info">
                  <h3>Hồ sơ hình thể & Biểu đồ số đo</h3>
                  <p>
                    Theo dõi biểu đồ thay đổi số đo ngực, eo, mông theo thời gian, xem lịch sử và so
                    sánh đối chiếu giữa hai lần chụp bất kỳ.
                  </p>
                  <div className="nav-card-stats-pills">
                    <span className="stat-pill">
                      {loadingScans ? "Đang tải…" : `${totalScans ?? 0} lần scan đã lưu`}
                    </span>
                    {latestScan && (
                      <span className="stat-pill">
                        Lần gần nhất: {formatScanDateTime(latestScan.captured_at)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="nav-card-arrow">
                <ChevronRight size={22} />
              </div>
            </Link>

            {/* Account Overview Grid */}
            <div className="account-overview-grid">
              {/* Profile Details Card */}
              <div className="account-card-panel">
                <div className="panel-header-title">
                  <UserIcon size={20} />
                  <span>Thông tin cá nhân</span>
                </div>

                <div className="user-profile-info-row">
                  <div className="user-avatar-badge">
                    {user.display_name.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
                  </div>

                  <div className="user-info-text">
                    {!editingName ? (
                      <div className="user-display-name-view">
                        <span>{user.display_name}</span>
                        <button
                          type="button"
                          className="btn-inline-edit"
                          onClick={() => {
                            setDisplayNameInput(user.display_name);
                            setEditingName(true);
                          }}
                          aria-label="Chỉnh sửa tên hiển thị"
                        >
                          <Edit3 size={13} /> Sửa tên
                        </button>
                      </div>
                    ) : (
                      <form onSubmit={handleSaveName} className="edit-name-form">
                        <input
                          type="text"
                          className="edit-name-input"
                          value={displayNameInput}
                          onChange={(e) => setDisplayNameInput(e.target.value)}
                          placeholder="Nhập tên hiển thị"
                          autoFocus
                          disabled={savingName}
                        />
                        <button
                          type="submit"
                          className="btn-gold-primary"
                          style={{ padding: "8px 14px", fontSize: 13 }}
                          disabled={savingName}
                        >
                          {savingName ? <LoaderCircle size={14} className="spin-gold" /> : <Check size={14} />} Lưu
                        </button>
                        <button
                          type="button"
                          className="btn-gold-secondary"
                          style={{ padding: "8px 12px", fontSize: 13 }}
                          onClick={() => {
                            setEditingName(false);
                            setNameError("");
                          }}
                          disabled={savingName}
                        >
                          <X size={14} />
                        </button>
                      </form>
                    )}

                    {nameError && (
                      <p style={{ color: "#9E2A2B", fontSize: 12, margin: "4px 0 0 0" }}>
                        {nameError}
                      </p>
                    )}

                    <div className="user-email-text">{user.email}</div>
                  </div>
                </div>

                {/* Account Security & Timestamp */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: 12.5,
                    color: "var(--account-text-secondary)",
                    paddingTop: 16,
                    borderTop: "1px solid var(--account-border-subtle)",
                  }}
                >
                  <ShieldCheck size={16} color="var(--account-primary)" />
                  <span>
                    Tài khoản được bảo vệ bằng phiên bảo mật server-side HttpOnly cookie.
                  </span>
                </div>
              </div>

              {/* Preferences & Scan Settings Card */}
              <div className="account-card-panel">
                <div className="panel-header-title">
                  <Settings size={20} />
                  <span>Tùy chọn lưu trữ số đo</span>
                </div>

                <div className="setting-toggle-row">
                  <div className="toggle-info-col">
                    <h4>Tự động lưu kết quả scan</h4>
                    <p>
                      Mỗi khi hoàn thành quá trình quét hình thể 3D qua webcam, hệ thống sẽ tự động
                      lưu lại bộ số đo vào hồ sơ cá nhân của bạn để theo dõi biểu đồ.
                    </p>
                  </div>

                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={user.auto_save_scans}
                      onChange={handleToggleAutoSave}
                      disabled={savingToggle}
                      aria-label="Tự động lưu kết quả scan sau khi quét xong"
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                {toggleSuccessToast && (
                  <p
                    style={{
                      color: "#194E3D",
                      fontSize: 12.5,
                      fontWeight: 600,
                      marginTop: 10,
                      marginBottom: 0,
                    }}
                  >
                    ✓ {toggleSuccessToast}
                  </p>
                )}

                {/* Summary Stat Box */}
                <div
                  style={{
                    marginTop: 20,
                    padding: 16,
                    borderRadius: "var(--account-radius-card)",
                    background: "var(--account-surface-warm)",
                    border: "1px solid var(--account-border-subtle)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontSize: 12, color: "var(--account-text-muted)" }}>
                      Tổng số bản ghi đã lưu
                    </div>
                    <div
                      style={{
                        fontSize: 22,
                        fontWeight: 700,
                        color: "var(--account-text)",
                        marginTop: 2,
                      }}
                    >
                      {loadingScans ? "…" : totalScans ?? 0}
                    </div>
                  </div>

                  <Link href="/account/body-profile" className="btn-gold-outline">
                    Xem lịch sử scan <ArrowRight size={14} />
                  </Link>
                </div>
              </div>
            </div>
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}
