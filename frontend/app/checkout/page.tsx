"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, AlertCircle, Info, Lock, ShoppingBag, ShieldCheck, Loader2 } from "lucide-react";
import Header from "../../components/shop/Header";
import Footer from "../../components/shop/Footer";
import CartDrawer from "../../components/shop/CartDrawer";
import WishlistDrawer from "../../components/shop/WishlistDrawer";
import { useCart } from "../../lib/CartContext";
import { money } from "../../lib/catalog";

const FREE_SHIPPING_THRESHOLD = 500000;
const STANDARD_SHIPPING_FEE = 30000;

export default function CheckoutPage() {
  const router = useRouter();
  const { cart, subtotal, totalQuantity, clearCart, hydrated } = useCart();

  // Step 1 Customer Details State
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");

  // Validation & Submit State
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Quote State (verified by POST /api/orders/quote)
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [verifiedSubtotal, setVerifiedSubtotal] = useState<number | null>(null);
  const [verifiedShippingFee, setVerifiedShippingFee] = useState<number | null>(null);
  const [verifiedTotal, setVerifiedTotal] = useState<number | null>(null);

  // Generate idempotency key once per checkout form mount
  const [idempotencyKey] = useState(() => {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return `mph_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  });

  // Calculate pricing (with backend quote verification or client fallback)
  const displaySubtotal = verifiedSubtotal !== null ? verifiedSubtotal : subtotal;
  const isFree = displaySubtotal >= FREE_SHIPPING_THRESHOLD;
  const displayShipping =
    verifiedShippingFee !== null
      ? verifiedShippingFee
      : cart.length === 0
      ? 0
      : isFree
      ? 0
      : STANDARD_SHIPPING_FEE;
  const displayTotal = verifiedTotal !== null ? verifiedTotal : displaySubtotal + displayShipping;

  // Verify prices via POST /api/orders/quote
  useEffect(() => {
    if (!hydrated || cart.length === 0) return;

    let isMounted = true;
    setQuoteLoading(true);

    const verifyQuote = async () => {
      try {
        const res = await fetch("/api/orders/quote", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            items: cart.map((item) => ({
              productId: item.productId,
              productSlug: item.productSlug,
              name: item.name,
              color: item.color,
              size: item.size,
              quantity: item.quantity,
              price: item.price,
              image: item.image,
            })),
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            const sub = data.subtotal ?? data.sub_total ?? subtotal;
            const ship =
              data.shippingFee ?? data.shipping_fee ?? (sub >= FREE_SHIPPING_THRESHOLD ? 0 : STANDARD_SHIPPING_FEE);
            const tot = data.total ?? sub + ship;
            setVerifiedSubtotal(sub);
            setVerifiedShippingFee(ship);
            setVerifiedTotal(tot);
          }
        } else {
          // Backend quote endpoint fallback
          if (isMounted) {
            setVerifiedSubtotal(subtotal);
            setVerifiedShippingFee(subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : STANDARD_SHIPPING_FEE);
            setVerifiedTotal(subtotal + (subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : STANDARD_SHIPPING_FEE));
          }
        }
      } catch {
        if (isMounted) {
          setVerifiedSubtotal(subtotal);
          setVerifiedShippingFee(subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : STANDARD_SHIPPING_FEE);
          setVerifiedTotal(subtotal + (subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : STANDARD_SHIPPING_FEE));
        }
      } finally {
        if (isMounted) setQuoteLoading(false);
      }
    };

    verifyQuote();
    return () => {
      isMounted = false;
    };
  }, [cart, subtotal, hydrated]);

  const validateForm = (): Record<string, string> => {
    const errs: Record<string, string> = {};

    if (!fullName.trim()) {
      errs.fullName = "Vui lòng nhập họ và tên của bạn";
    } else if (fullName.trim().length < 2) {
      errs.fullName = "Họ và tên cần có ít nhất 2 ký tự";
    }

    const cleanPhone = phone.replace(/[^0-9]/g, "");
    if (!cleanPhone) {
      errs.phone = "Vui lòng nhập số điện thoại liên hệ";
    } else if (cleanPhone.length < 9 || cleanPhone.length > 11) {
      errs.phone = "Số điện thoại phải từ 9 đến 11 chữ số";
    }

    if (email.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email.trim())) {
        errs.email = "Email không đúng định dạng (ví dụ: ten@gmail.com)";
      }
    }

    if (!address.trim()) {
      errs.address = "Vui lòng nhập địa chỉ nhận hàng chi tiết";
    } else if (address.trim().length < 6) {
      errs.address = "Địa chỉ cần chi tiết hơn (số nhà, tên đường, phường/xã, quận/huyện, tỉnh/thành)";
    }

    return errs;
  };

  const handleOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    setSubmitError(null);

    const nextErrors = validateForm();
    setErrors(nextErrors);

    const errorKeys = Object.keys(nextErrors);
    if (errorKeys.length > 0) {
      // Focus and scroll to the first error field immediately using nextErrors
      const firstErrorKey = errorKeys[0];
      const el = document.getElementById(firstErrorKey);
      if (el) {
        el.focus();
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      return;
    }

    if (cart.length === 0) {
      setSubmitError("Giỏ hàng của bạn đang trống. Vui lòng thêm sản phẩm trước khi đặt hàng.");
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        customer: {
          name: fullName.trim(),
          phone: phone.trim(),
          email: email.trim() || undefined,
          address: address.trim(),
          notes: notes.trim() || undefined,
        },
        items: cart.map((item) => ({
          productId: item.productId,
          productSlug: item.productSlug,
          name: item.name,
          color: item.color,
          size: item.size,
          quantity: item.quantity,
          price: item.price,
          image: item.image,
        })),
        idempotencyKey,
      };

      const res = await fetch("/api/orders", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let msg = "Không thể tiếp nhận đơn hàng. Vui lòng kiểm tra lại thông tin.";
        try {
          const errData = await res.json();
          if (errData.detail) {
            msg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
          } else if (errData.message) {
            msg = errData.message;
          }
        } catch {}
        throw new Error(msg);
      }

      const data = await res.json();
      const orderId = data.orderId || data.id || data.order_id || data.code;
      const token = data.token || data.access_token || "";

      // On success: clear cart and redirect to order confirmation route
      clearCart();
      const redirectUrl = token
        ? `/orders/${encodeURIComponent(orderId)}?token=${encodeURIComponent(token)}`
        : `/orders/${encodeURIComponent(orderId)}`;
      router.push(redirectUrl);
    } catch (err: any) {
      setSubmitError(err?.message || "Đã xảy ra lỗi khi gửi đơn hàng. Vui lòng thử lại sau.");
      setIsSubmitting(false);
    }
  };

  if (!hydrated) {
    return (
      <div className="storefront">
        <Header />
        <main className="checkout-page">
          <div className="checkout-container">
            <p>Đang tải trang đặt hàng…</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (cart.length === 0) {
    return (
      <div className="storefront">
        <Header />
        <main className="checkout-page">
          <div className="checkout-container">
            <div className="cart-empty-view">
              <ShoppingBag size={56} strokeWidth={1.2} />
              <h2>Giỏ hàng đang trống</h2>
              <p>Bạn không có sản phẩm nào trong giỏ để tiến hành đặt hàng.</p>
              <Link href="/#catalog" className="shop-primary">
                Khám phá bộ sưu tập
                <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="storefront">
      <Header />
      <CartDrawer />
      <WishlistDrawer />

      <main className="checkout-page">
        <div className="checkout-container">
          {/* Visual Step Indicator */}
          <nav aria-label="Tiến trình đặt hàng" className="checkout-stepper">
            <div className="checkout-step-pill completed">
              <span className="checkout-step-num"><CheckCircle2 size={14} /></span>
              <span>1. Giỏ hàng</span>
            </div>
            <div className="checkout-step-line" />
            <div className="checkout-step-pill active" aria-current="step">
              <span className="checkout-step-num">2</span>
              <span>2. Thông tin nhận hàng</span>
            </div>
            <div className="checkout-step-line" />
            <div className="checkout-step-pill">
              <span className="checkout-step-num">3</span>
              <span>3. Xác nhận đơn</span>
            </div>
          </nav>

          {/* Global Submit Error Banner */}
          {submitError && (
            <div className="error-message" role="alert" style={{ marginBottom: 24, fontSize: 13 }}>
              <AlertCircle size={18} />
              <div>
                <strong>Không thể hoàn tất đơn hàng:</strong>
                <p style={{ margin: "4px 0 0" }}>{submitError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleOrderSubmit} noValidate>
            <div className="checkout-layout">
              {/* Left Column: Customer details & Order review */}
              <div className="checkout-main-content">
                {/* Step 1: Customer Details Form */}
                <section className="checkout-section-card" aria-labelledby="shipping-heading">
                  <h2 id="shipping-heading">
                    <ShieldCheck size={20} color="var(--primary)" />
                    1. Thông tin người nhận hàng (Khách mua nhanh)
                  </h2>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "-10px 0 20px" }}>
                    Đặt hàng không cần tạo tài khoản. Chúng tôi sẽ liên hệ để xác nhận thời gian giao hàng.
                  </p>

                  <div className="checkout-form-grid">
                    {/* Họ và tên (required) */}
                    <div className={`checkout-field-group ${errors.fullName ? "has-error" : ""}`}>
                      <label htmlFor="fullName">
                        Họ và tên <span style={{ color: "var(--danger)" }}>*</span>
                      </label>
                      <input
                        id="fullName"
                        type="text"
                        placeholder="Nguyễn Văn A"
                        value={fullName}
                        onChange={(e) => {
                          setFullName(e.target.value);
                          if (errors.fullName) setErrors((prev) => ({ ...prev, fullName: "" }));
                        }}
                        autoComplete="name"
                        aria-invalid={!!errors.fullName}
                        aria-describedby={errors.fullName ? "fullName-error" : undefined}
                        required
                      />
                      {errors.fullName && (
                        <span id="fullName-error" className="checkout-field-error" role="alert">
                          {errors.fullName}
                        </span>
                      )}
                    </div>

                    {/* Số điện thoại (required, 9-11 digits) */}
                    <div className={`checkout-field-group ${errors.phone ? "has-error" : ""}`}>
                      <label htmlFor="phone">
                        Số điện thoại <span style={{ color: "var(--danger)" }}>*</span>
                      </label>
                      <input
                        id="phone"
                        type="tel"
                        placeholder="0912 345 678"
                        value={phone}
                        onChange={(e) => {
                          setPhone(e.target.value);
                          if (errors.phone) setErrors((prev) => ({ ...prev, phone: "" }));
                        }}
                        autoComplete="tel"
                        aria-invalid={!!errors.phone}
                        aria-describedby={errors.phone ? "phone-error" : undefined}
                        required
                      />
                      {errors.phone && (
                        <span id="phone-error" className="checkout-field-error" role="alert">
                          {errors.phone}
                        </span>
                      )}
                    </div>

                    {/* Email (optional) */}
                    <div className={`checkout-field-group full-col ${errors.email ? "has-error" : ""}`}>
                      <label htmlFor="email">
                        Email <span style={{ color: "var(--text-secondary)", fontWeight: 400 }}>(Không bắt buộc, để nhận thông báo đơn)</span>
                      </label>
                      <input
                        id="email"
                        type="email"
                        placeholder="email@example.com"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (errors.email) setErrors((prev) => ({ ...prev, email: "" }));
                        }}
                        autoComplete="email"
                        aria-invalid={!!errors.email}
                        aria-describedby={errors.email ? "email-error" : undefined}
                      />
                      {errors.email && (
                        <span id="email-error" className="checkout-field-error" role="alert">
                          {errors.email}
                        </span>
                      )}
                    </div>

                    {/* Địa chỉ nhận hàng (required, input rõ ràng không dropdown sai) */}
                    <div className={`checkout-field-group full-col ${errors.address ? "has-error" : ""}`}>
                      <label htmlFor="address">
                        Địa chỉ nhận hàng chi tiết <span style={{ color: "var(--danger)" }}>*</span>
                      </label>
                      <textarea
                        id="address"
                        rows={3}
                        placeholder="Số nhà, tên đường, phường/xã, quận/huyện, tỉnh/thành phố"
                        value={address}
                        onChange={(e) => {
                          setAddress(e.target.value);
                          if (errors.address) setErrors((prev) => ({ ...prev, address: "" }));
                        }}
                        autoComplete="street-address"
                        aria-invalid={!!errors.address}
                        aria-describedby={errors.address ? "address-error" : undefined}
                        required
                      />
                      {errors.address && (
                        <span id="address-error" className="checkout-field-error" role="alert">
                          {errors.address}
                        </span>
                      )}
                    </div>

                    {/* Ghi chú đơn hàng (optional) */}
                    <div className="checkout-field-group full-col">
                      <label htmlFor="notes">
                        Ghi chú đơn hàng <span style={{ color: "var(--text-secondary)", fontWeight: 400 }}>(Ví dụ: giao trong giờ hành chính, gọi trước khi giao)</span>
                      </label>
                      <textarea
                        id="notes"
                        rows={2}
                        placeholder="Yêu cầu đặc biệt về thời gian hoặc địa điểm giao hàng…"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                      />
                    </div>
                  </div>
                </section>

                {/* Explicit Disclaimer: Tiếp nhận đơn hàng, chưa hỗ trợ thanh toán online */}
                <div className="checkout-disclaimer-box" role="note">
                  <div className="disclaimer-header">
                    <Info size={19} />
                    <span>Chính sách tiếp nhận đơn hàng</span>
                  </div>
                  <p>
                    <strong>Hệ thống hiện tiếp nhận đơn hàng, chưa hỗ trợ thanh toán trực tuyến.</strong>
                  </p>
                  <p className="disclaimer-sub">
                    Quý khách không cần thanh toán ngay tại trang web. Sau khi gửi đơn, chuyên viên
                    tư vấn của MORPH Studio sẽ gọi điện hoặc gửi tin nhắn SMS để xác nhận lại số đo
                    hình thể, kiểm tra size trang phục và hẹn lịch giao hàng (thanh toán khi nhận hàng - COD).
                  </p>
                </div>

                <div style={{ marginTop: 10 }}>
                  <Link href="/cart" className="cart-continue-link" style={{ justifyContent: "flex-start" }}>
                    <ArrowLeft size={16} />
                    <span>Quay lại chỉnh sửa giỏ hàng</span>
                  </Link>
                </div>
              </div>

              {/* Right Column: Step 2 Review order & Pricing summary */}
              <aside className="checkout-sidebar" aria-label="Tóm tắt và xác nhận đơn hàng">
                <div className="checkout-section-card" style={{ position: "sticky", top: 96 }}>
                  <h2>
                    <ShoppingBag size={18} color="var(--primary)" />
                    2. Danh sách sản phẩm ({totalQuantity})
                  </h2>

                  {/* Item review list */}
                  <div className="checkout-item-review-list">
                    {cart.map((item) => (
                      <div className="checkout-item-review-row" key={item.id}>
                        <div className="checkout-item-thumb">
                          <img
                            src={item.image}
                            alt={item.name}
                            width="56"
                            height="70"
                            onError={(e) => {
                              e.currentTarget.src = "/products/v2/ao-thun-essential.jpg";
                            }}
                          />
                        </div>
                        <div className="checkout-item-info">
                          <div className="checkout-item-name">{item.name}</div>
                          <div className="checkout-item-variant">
                            Màu: {item.color} · Size: <strong>{item.size}</strong> · SL: <strong>{item.quantity}</strong>
                          </div>
                        </div>
                        <div className="checkout-item-price">
                          {money(item.price * item.quantity)}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pricing Breakdown */}
                  <div className="cart-summary-rows" style={{ borderTop: "1px solid var(--line)", paddingTop: 16 }}>
                    <div className="cart-summary-row">
                      <span>Tạm tính</span>
                      <span>
                        {quoteLoading ? (
                          <span style={{ fontSize: 12, color: "var(--muted)" }}>Đang đối chiếu…</span>
                        ) : (
                          <strong>{money(displaySubtotal)}</strong>
                        )}
                      </span>
                    </div>

                    <div className="cart-summary-row">
                      <span>Phí giao hàng</span>
                      <span>
                        {displayShipping === 0 ? (
                          <span className="shipping-free-badge">Miễn phí</span>
                        ) : (
                          <strong>{money(displayShipping)}</strong>
                        )}
                      </span>
                    </div>

                    <div className="cart-summary-row total-row">
                      <span>Tổng tiền cần thanh toán</span>
                      <strong>{money(displayTotal)}</strong>
                    </div>
                  </div>

                  {/* Final CTA: Xác nhận đặt hàng */}
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="shop-primary cart-checkout-cta"
                    style={{ width: "100%", marginTop: 18 }}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 size={18} className="animate-spin" />
                        <span>Đang tiếp nhận đơn…</span>
                      </>
                    ) : (
                      <>
                        <Lock size={16} />
                        <span>Xác nhận đặt hàng</span>
                      </>
                    )}
                  </button>

                  <div style={{ textAlign: "center", marginTop: 12, fontSize: 12, color: "var(--text-secondary)" }}>
                    Cam kết bảo mật thông tin · Hỗ trợ đổi trả 7 ngày
                  </div>
                </div>
              </aside>
            </div>
          </form>
        </div>
      </main>

      <Footer />
    </div>
  );
}
