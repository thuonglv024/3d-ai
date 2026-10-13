"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useRef, useEffect, Suspense } from "react";
import {
  Heart,
  Search,
  ShoppingBag,
  Menu,
  X,
  ArrowRight,
  Sparkles,
  User,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { useCart } from "../../lib/CartContext";
import { useAuth } from "../../lib/AuthContext";
import { CATEGORIES } from "../../lib/catalog";
import { useDrawerA11y } from "../../lib/useDrawerA11y";
import { buildAuthUrl } from "../../lib/authNav";

function HeaderFallback() {
  return (
    <>
      <div className="shop-announcement">
        <span className="announcement-brand">MORPH STUDIO</span>
        <span className="announcement-divider">·</span>
        <span>Mô phỏng hình thể 3D & gợi ý size</span>
        <span className="announcement-divider">·</span>
        <span>Ước lượng hình thể tham khảo qua 2 góc chụp webcam</span>
      </div>

      <header className="shop-header">
        <button
          className="mobile-nav-toggle shop-icon"
          aria-label="Mở menu"
        >
          <Menu size={22} />
        </button>

        <Link href="/" className="shop-logo" aria-label="MORPH Studio trang chủ">
          MORPH<span>STUDIO</span>
        </Link>

        <nav aria-label="Danh mục sản phẩm" className="desktop-nav">
          <Link href="/" className="active">
            Tất cả
          </Link>
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.key}
              href={`/?category=${cat.key}#catalog`}
            >
              {cat.name}
            </Link>
          ))}
          <Link href="/scan" className="nav-scan-link">
            <Sparkles size={13} />
            <span>Phòng thử 3D</span>
          </Link>
        </nav>

        <div className="header-actions">
          <button
            className="shop-icon header-search-btn"
            aria-label="Tìm kiếm sản phẩm"
          >
            <Search size={20} />
          </button>

          <button
            className="shop-icon header-account-btn"
            aria-label="Tài khoản"
          >
            <User size={20} />
          </button>

          <button
            className="shop-icon header-wishlist-btn"
            aria-label="Sản phẩm yêu thích"
          >
            <Heart size={20} />
          </button>

          <Link
            href="/cart"
            className="shop-bag"
            aria-label="Xem giỏ hàng"
          >
            <ShoppingBag size={20} />
            <span>Giỏ hàng</span>
          </Link>
        </div>
      </header>
    </>
  );
}

function HeaderContent() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { totalQuantity, wishlist, setIsWishlistOpen } = useCart();
  const { user, logout } = useAuth();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const accountBtnRef = useRef<HTMLButtonElement>(null);

  useDrawerA11y(mobileMenuOpen, () => setMobileMenuOpen(false), mobileMenuRef);

  // Close account menu on click outside or Escape key
  useEffect(() => {
    if (!userMenuOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setUserMenuOpen(false);
        accountBtnRef.current?.focus();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [userMenuOpen]);

  const currentCategory = searchParams?.get("category") || "";

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/?q=${encodeURIComponent(searchQuery.trim())}#catalog`);
      setSearchOpen(false);
    }
  };

  const getShortName = (fullName: string) => {
    const parts = fullName.trim().split(/\s+/);
    return parts[parts.length - 1] || fullName;
  };

  return (
    <>
      <div className="shop-announcement">
        <span className="announcement-brand">MORPH STUDIO</span>
        <span className="announcement-divider">·</span>
        <span>Mô phỏng hình thể 3D & gợi ý size</span>
        <span className="announcement-divider">·</span>
        <span>Ước lượng hình thể tham khảo qua 2 góc chụp webcam</span>
      </div>

      <header className="shop-header">
        <button
          className="mobile-nav-toggle shop-icon"
          aria-label={mobileMenuOpen ? "Đóng menu" : "Mở menu"}
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        <Link href="/" className="shop-logo" aria-label="MORPH Studio trang chủ">
          MORPH<span>STUDIO</span>
        </Link>

        {/* Center-aligned luxury fashion navigation bar */}
        <nav aria-label="Danh mục sản phẩm" className="desktop-nav">
          <Link
            href="/"
            className={pathname === "/" && !currentCategory ? "active" : ""}
          >
            Tất cả
          </Link>
          {CATEGORIES.map((cat) => {
            const isActive = pathname === "/" && currentCategory === cat.key;
            return (
              <Link
                key={cat.key}
                href={`/?category=${cat.key}#catalog`}
                className={isActive ? "active" : ""}
              >
                {cat.name}
              </Link>
            );
          })}
          <Link href="/scan" className="nav-scan-link">
            <Sparkles size={13} />
            <span>Phòng thử 3D</span>
          </Link>
        </nav>

        <div className="header-actions">
          {searchOpen ? (
            <form onSubmit={handleSearchSubmit} className="header-search-form">
              <input
                type="text"
                placeholder="Tìm áo, quần, váy..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
                className="header-search-input"
              />
              <button type="submit" className="shop-icon" aria-label="Tìm kiếm">
                <Search size={18} />
              </button>
              <button
                type="button"
                className="shop-icon"
                onClick={() => setSearchOpen(false)}
                aria-label="Đóng tìm kiếm"
              >
                <X size={18} />
              </button>
            </form>
          ) : (
            <button
              className="shop-icon header-search-btn"
              aria-label="Tìm kiếm sản phẩm"
              onClick={() => setSearchOpen(true)}
            >
              <Search size={20} />
            </button>
          )}

          {/* User Account / Auth Link */}
          {!user ? (
            <Link
              href={buildAuthUrl("login", { returnTo: pathname })}
              className="shop-icon header-account-btn"
              aria-label="Đăng nhập / Tạo tài khoản"
            >
              <User size={20} />
            </Link>
          ) : (
            <div className="header-account-container" ref={userMenuRef}>
              <button
                ref={accountBtnRef}
                className="header-account-pill"
                aria-label={`Tài khoản: ${user.display_name}`}
                aria-expanded={userMenuOpen}
                onClick={() => setUserMenuOpen(!userMenuOpen)}
              >
                <span className="header-user-avatar">
                  {user.display_name.charAt(0).toUpperCase()}
                </span>
                <span className="header-user-name">
                  {getShortName(user.display_name)}
                </span>
                <ChevronDown
                  size={14}
                  className={`header-user-chevron ${userMenuOpen ? "is-open" : ""}`}
                />
              </button>

              {userMenuOpen && (
                <div
                  className="custom-dropdown-menu account-dropdown-menu is-align-right"
                  role="menu"
                  aria-label="Menu tài khoản"
                >
                  <div className="account-dropdown-profile">
                    <span className="account-avatar-lg">
                      {user.display_name.charAt(0).toUpperCase()}
                    </span>
                    <div className="account-profile-info">
                      <strong className="account-display-name">{user.display_name}</strong>
                      <span className="account-email">{user.email}</span>
                    </div>
                  </div>

                  <div className="dropdown-divider" />

                  <Link
                    href="/account"
                    className="dropdown-option-item account-menu-link"
                    role="menuitem"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <User size={16} />
                    <span>Hồ sơ của tôi</span>
                  </Link>

                  <Link
                    href="/account/body-profile"
                    className="dropdown-option-item account-menu-link"
                    role="menuitem"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <Sparkles size={16} />
                    <span>Hồ sơ hình thể & Số đo 3D</span>
                  </Link>

                  <div className="dropdown-divider" />

                  <button
                    type="button"
                    className="dropdown-option-item account-menu-link is-logout"
                    role="menuitem"
                    onClick={async () => {
                      setUserMenuOpen(false);
                      await logout();
                    }}
                  >
                    <LogOut size={16} />
                    <span>Đăng xuất</span>
                  </button>
                </div>
              )}
            </div>
          )}

          <button
            className="shop-icon header-wishlist-btn"
            aria-label={`Sản phẩm yêu thích (${wishlist.length})`}
            onClick={() => setIsWishlistOpen(true)}
          >
            <Heart size={20} fill={wishlist.length > 0 ? "currentColor" : "none"} />
            {wishlist.length > 0 && <span className="action-badge">{wishlist.length}</span>}
          </button>

          <Link
            href="/cart"
            className="shop-bag"
            aria-label={`Xem giỏ hàng, ${totalQuantity} sản phẩm`}
          >
            <ShoppingBag size={20} />
            <span>Giỏ hàng</span>
            <b>{totalQuantity}</b>
          </Link>
        </div>
      </header>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div
          className="mobile-menu-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Menu điều hướng"
        >
          <div
            ref={mobileMenuRef}
            tabIndex={-1}
            className="mobile-menu-content"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mobile-menu-header">
              <span className="shop-logo">
                MORPH<span>STUDIO</span>
              </span>
              <button
                className="shop-icon"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Đóng menu"
              >
                <X size={20} />
              </button>
            </div>

            {/* Mobile Account Section */}
            {user ? (
              <div className="mobile-account-section">
                <div className="mobile-account-header">
                  <span className="mobile-account-avatar">
                    {user.display_name.charAt(0).toUpperCase()}
                  </span>
                  <div className="mobile-account-info">
                    <strong className="mobile-account-name">{user.display_name}</strong>
                    <span className="mobile-account-email">{user.email}</span>
                  </div>
                </div>
                <div className="mobile-account-actions">
                  <Link
                    href="/account"
                    onClick={() => setMobileMenuOpen(false)}
                    className="mobile-account-sublink"
                  >
                    <User size={16} />
                    <span>Hồ sơ của tôi</span>
                  </Link>
                  <Link
                    href="/account/body-profile"
                    onClick={() => setMobileMenuOpen(false)}
                    className="mobile-account-sublink"
                  >
                    <Sparkles size={16} />
                    <span>Hồ sơ hình thể & Số đo 3D</span>
                  </Link>
                  <button
                    type="button"
                    className="mobile-account-sublink is-logout"
                    onClick={async () => {
                      setMobileMenuOpen(false);
                      await logout();
                    }}
                  >
                    <LogOut size={16} />
                    <span>Đăng xuất</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="mobile-guest-auth-box">
                <Link
                  href={buildAuthUrl("login", { returnTo: pathname })}
                  className="mobile-guest-auth-btn"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <User size={18} />
                  <span>Đăng nhập / Đăng ký</span>
                </Link>
                <Link
                  href="/account/body-profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className="mobile-guest-profile-link"
                >
                  <Sparkles size={14} />
                  <span>Hồ sơ hình thể & Số đo 3D</span>
                </Link>
              </div>
            )}

            <div className="mobile-menu-divider" />

            <nav className="mobile-menu-links">
              <Link
                href="/"
                onClick={() => setMobileMenuOpen(false)}
                className={!currentCategory ? "active" : ""}
              >
                Tất cả sản phẩm
              </Link>
              {CATEGORIES.map((cat) => (
                <Link
                  key={cat.key}
                  href={`/?category=${cat.key}#catalog`}
                  onClick={() => setMobileMenuOpen(false)}
                  className={currentCategory === cat.key ? "active" : ""}
                >
                  {cat.name}
                </Link>
              ))}
              <Link
                href="/cart"
                onClick={() => setMobileMenuOpen(false)}
                className={pathname === "/cart" ? "active" : ""}
              >
                Giỏ hàng ({totalQuantity})
              </Link>
              <div className="mobile-menu-divider" />
              <Link href="/scan" onClick={() => setMobileMenuOpen(false)}>
                Công cụ scan 3D độc lập <ArrowRight size={15} />
              </Link>
            </nav>
          </div>
        </div>
      )}
    </>
  );
}

export default function Header() {
  return (
    <Suspense fallback={<HeaderFallback />}>
      <HeaderContent />
    </Suspense>
  );
}
