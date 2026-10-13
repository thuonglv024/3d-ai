---
name: MORPH Studio
description: Luxury warm ivory and champagne gold fashion e-commerce storefront with integrated 3D webcam fitting studio and complete ordering workflow.
colors:
  bg-app: "#FAF7F0"
  bg-surface: "#FFFFFF"
  surface-card: "#FFFFFF"
  surface-subtle: "#F4F0E8"
  surface-well: "#EBE5D8"
  primary: "#C6A15B"
  primary-hover: "#B58F49"
  primary-light: "#F7F1E3"
  on-primary: "#26211A"
  text-primary: "#26211A"
  text-secondary: "#5C564D"
  text-muted: "#8C8479"
  border: "#E5DEC9"
  border-subtle: "#EFE9DB"
  contour-chest: "#C6A15B"
  contour-waist: "#9E6D38"
  contour-hip: "#2D5A7B"
  success: "#194E3D"
  success-bg: "#EEF6EE"
  danger: "#9E2A2B"
  danger-bg: "#FBEFED"
typography:
  display:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "clamp(30px, 3.2vw, 46px)"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "26px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.025em"
  result-title:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "14px"
    lineHeight: 1.6
  label:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "12px"
    fontWeight: 500
  data:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "16px"
    fontWeight: 700
rounded:
  control: "12px"
  card: "18px"
  container: "20px"
  modal: "24px"
  drawer: "24px"
  pill: "9999px"
spacing:
  tight: "8px"
  label: "12px"
  field: "16px"
  control: "20px"
  section: "24px"
  result: "24px"
---

# Design System: MORPH Studio

## 1. Triết lý Thiết kế (Creative North Star)

**"Sự ấm áp của thời trang cao cấp gặp gỡ công nghệ mô phỏng hình thể 3D"**

MORPH Studio là một nền tảng thương mại điện tử thời trang may mặc kết hợp phòng thử đồ số (Virtual Fitting Studio). Toàn bộ trải nghiệm được xây dựng trên bảng màu **Warm Ivory (Ngà ấm) & Champagne Gold (Vàng sâm-panh)**, mang lại cảm giác thanh lịch, cao cấp nhưng thân thiện và đáng tin cậy.

Hệ thống tuân thủ nghiêm ngặt các nguyên tắc:
1. **Minh bạch & Đáng tin cậy**: Không tuyên bố quá mức về số đo tuyệt đối hay công nghệ viển vông; mô hình 3D đóng vai trò tham khảo trực quan và đối chiếu tỷ lệ với bảng size chuẩn.
2. **Liền mạch (Context Preservation)**: Tìm size qua webcam không ngắt quãng trải nghiệm mua sắm. Biến thể màu, sản phẩm đang xem và vị trí cuộn được bảo tồn nguyên vẹn.
3. **Độ tương phản & Khả năng tiếp cận (Accessibility WCAG AA)**: Các nút bấm chính (Primary CTA) sử dụng chữ tối `#26211A` trên nền vàng sâm-panh `#C6A15B` đạt tỷ lệ tương phản **6.58:1** (vượt chuẩn WCAG AA 4.5:1).
4. **Chuẩn hóa Bo góc (Radius Hierarchy)**:
   - Các nút bấm, ô nhập liệu, dropdown (`control`): **12px**
   - Thẻ sản phẩm, bảng giá (`card`): **18px**
   - Khung chứa chính, tóm tắt đơn (`container`): **20px**
   - Hộp thoại nổi, ngăn kéo (`modal`, `drawer`): **24px**
   - Huy hiệu, thanh trạng thái (`badge`, `pill`): **9999px (Pill)**

---

## 2. Hệ thống Token & Màu sắc

### 2.1 Bảng màu cốt lõi
- **Nền ứng dụng (`--bg-app`)**: `#FAF7F0` (Ivory ngà ấm, không dùng trắng toát chói mắt).
- **Mặt nền thẻ (`--surface-card`)**: `#FFFFFF` (Trắng tinh khiết tạo phân tầng với nền ngà).
- **Mặt nền phụ (`--surface-subtle`)**: `#F4F0E8` (Đệm cho vùng phụ trợ, sân khấu 3D, thanh tóm tắt).
- **Màu nhấn thương hiệu (`--primary`)**: `#C6A15B` (Champagne Gold).
- **Màu nhấn Hover (`--primary-hover`)**: `#B58F49`.
- **Màu chữ trên nền nhấn (`--on-primary`)**: `#26211A` (Nâu đen đậm, bảo đảm tương phản 6.58:1).
- **Chữ chính (`--text-primary`)**: `#26211A`.
- **Chữ phụ (`--text-secondary`)**: `#5C564D`.
- **Chữ mờ (`--text-muted`)**: `#8C8479`.
- **Đường viền (`--border`)**: `#E5DEC9`.

### 2.2 Màu trạng thái & Đường đo 3D
- **Thành công (`--success`)**: `#194E3D` / Nền: `#EEF6EE`.
- **Cảnh báo (`--warning`)**: `#8F5819` / Nền: `#FCF2E3`.
- **Lỗi / Xóa (`--danger`)**: `#9E2A2B` / Nền: `#FBEFED`.
- **Vòng ngực 3D (`contour-chest`)**: `#C6A15B` (Gold).
- **Vòng eo 3D (`contour-waist`)**: `#9E6D38` (Amber).
- **Vòng mông 3D (`contour-hip`)**: `#2D5A7B` (Slate Blue).

---

## 3. Kiến trúc Luồng Thương Mại Điện Tử (E-Commerce Architecture)

### 3.1 Header & Bounding Box An Toàn
- **Thanh thông báo (`.shop-announcement`)**: Nền vàng ngà ấm với thông điệp thực tế về mô phỏng 3D tham khảo.
- **Thanh điều hướng (`.shop-header`)**:
  - Logo MORPH Studio căn trái, menu danh mục trang nhã căn giữa, công cụ tìm kiếm, danh sách yêu thích và nút Giỏ hàng căn phải.
  - Nút giỏ hàng hiển thị badge số lượng sản phẩm được đồng bộ tự động với `CartContext`.
  - Trên mobile (390px và 360px), header sử dụng cấu trúc `flex-wrap: nowrap` với khoảng cách an toàn, bảo đảm nút giỏ hàng và huy hiệu không bao giờ bị cắt mép màn hình (`isClipped: false`).

### 3.2 Trang Chi Tiết Sản Phẩm (`/products/[slug]`)
- **Hiển thị hình ảnh chuẩn xác**: Ảnh thumbnail và gallery phản ánh đúng sản phẩm thực tế từ kho thời trang MORPH Studio.
- **Lựa chọn màu sắc & Chú thích rõ ràng**: Khi chọn màu sắc biến thể phụ chưa có ảnh chụp riêng, hệ thống hiển thị dòng chú thích minh bạch: *"Ảnh hiển thị màu gốc: [Tên màu]"*.
- **Xác thực Size từ URL**: Không tự động chấp nhận chuỗi size không có trong danh mục của sản phẩm.
- **Thêm vào giỏ hàng tinh tế**: Bấm "Thêm vào giỏ" sẽ cập nhật badge giỏ hàng và hiển thị thanh thông báo nổi tại trang (`.product-added-banner`) kèm liên kết dẫn đến trang Giỏ hàng `/cart`.

### 3.3 Trang Giỏ Hàng Toàn Diện (`/cart`)
- **Chế độ xem bảng trên Desktop & danh sách thẻ trên Mobile**:
  - Từng dòng sản phẩm hỗ trợ đổi màu sắc và đổi size trực tiếp ngay trong giỏ hàng.
  - Bộ điều khiển số lượng (Stepper `+` / `-`) với giới hạn từ 1 đến 10.
  - Nút Xóa có hỗ trợ thông báo Hoàn tác (Undo Toast) trong 7 giây, cho phép người dùng khôi phục sản phẩm nếu bấm nhầm.
- **Khối Tóm tắt Đơn hàng Dính (`sticky aside`)**:
  - Thanh tiến trình Miễn phí vận chuyển: Đơn hàng từ **500.000đ** trở lên được miễn phí vận chuyển (tiết kiệm 30.000đ).
  - Tạm tính, phí giao hàng và tổng thanh toán hiển thị rõ ràng bằng định dạng tiền tệ VNĐ.
  - Nút CTA chính "Tiến hành đặt hàng" bo góc 12px, nền Gold, chữ đen đậm.

### 3.4 Trang Đặt Hàng Nhanh (`/checkout`)
- **Tiến trình 3 bước trực quan (`.checkout-stepper`)**: 1. Giỏ hàng $\rightarrow$ 2. Thông tin nhận hàng (đang kích hoạt) $\rightarrow$ 3. Xác nhận đơn.
- **Hình thức Mua hàng Không cần Tài khoản (Guest Checkout)**:
  - Form nhập thông tin ngắn gọn: Họ và tên (`#fullName`), Số điện thoại (`#phone`), Email (`#email`, không bắt buộc), Địa chỉ nhận hàng chi tiết (`#address`), Ghi chú đơn hàng (`#notes`).
  - Kiểm tra tính hợp lệ tức thời (Validate tên $\ge 2$ ký tự, số điện thoại 9–11 chữ số, địa chỉ $\ge 6$ ký tự).
- **Xác thực Báo giá từ Backend (`POST /api/orders/quote`)**:
  - Mỗi thay đổi giỏ hàng đều được tính toán lại qua API backend thật để tránh sai lệch đơn giá hoặc phí giao hàng.
- **Thông báo Chính sách Tiếp nhận Đơn hàng (`.checkout-disclaimer-box`)**:
  - Ghi chú minh bạch: MORPH Studio áp dụng hình thức tiếp nhận đơn hàng và gọi điện xác nhận size trước khi giao. Không giả mạo cổng thanh toán trực tuyến hoặc thẻ ngân hàng chưa được ủy quyền.
- **Chống Đặt Trùng Lặp (Idempotency Key)**:
  - Mỗi phiên đặt hàng tạo một khóa `Idempotency-Key` duy nhất, bảo vệ hệ thống khỏi các cú nhấp chuột đúp hoặc mạng chập chờn.

### 3.5 Trang Xác Nhận & Tra Cứu Đơn Hàng (`/orders/[id]?token=[token]`)
- **Mã đơn hàng độc bản**: Chuỗi mã định dạng `MPH-YYYYMMDD-XXXX` (ví dụ `MPH-20261013-4328`).
- **Nút Sao chép Mã tiện lợi**: Copy mã vào clipboard với hiệu ứng phản hồi tức thì "Đã chép".
- **Huy hiệu trạng thái**: Mặc định hiển thị badge xanh `Đã tiếp nhận`.
- **Bảo mật truy cập bằng Token**:
  - Chi tiết đơn hàng (thông tin khách hàng, số điện thoại, địa chỉ, danh sách món hàng) chỉ hiển thị khi có mã bí mật `token` hợp lệ trong URL hoặc header `X-Order-Token`.
  - Nếu token thiếu hoặc không khớp, hệ thống hiển thị thông báo lỗi bảo mật an toàn (`.order-error-card`) và không để lộ dữ liệu nhạy cảm.

---

## 4. Trải Nghiệm Phòng Thử Đồ 3D (`FitExperience`)

### 4.1 Bảng Size Chuẩn & Liên Kết Scan
- Modal Bảng size hiển thị bảng số đo cơ thể tham khảo cho áo hoặc quần/váy.
- Nút "Tìm size bằng webcam 3D" cho phép chuyển đổi mượt mà sang module quét camera mà không bị xung đột cuộn hay mất ngữ cảnh.

### 4.2 Luồng Camera Chỉ Dẫn Hai Góc
- Yêu cầu người dùng đồng ý trước khi kích hoạt webcam.
- Nhập chiều cao thực tế (100–230 cm) để làm chuẩn tỷ lệ.
- Hướng dẫn tư thế và đếm ngược 5 giây chụp góc Chính diện $\rightarrow$ Nhắc xoay 90° $\rightarrow$ Đếm ngược 5 giây chụp góc Nghiêng.
- Hỗ trợ đổi camera trong phiên, thông báo lỗi rõ ràng nếu webcam bị mất kết nối.

### 4.3 Kết Quả Khớp Dáng & Áp Dụng Size
- Sân khấu 3D nền sáng với mô hình body MakeHuman biến dạng theo đường viền segmentation từ ảnh webcam.
- Bảng gợi ý size hiển thị nổi bật ở đầu trang kết quả.
- Nút "Áp dụng size [X] →" gán size được gợi ý vào sản phẩm đang xem và đóng modal nhẹ nhàng.
- Nút phụ "Xem bảng size & chọn thủ công" và "Quét lại toàn thân" hỗ trợ xử lý linh hoạt cho mọi trường hợp.

---

## 5. Danh Sách Token CSS Hoàn Chỉnh (`frontend/app/globals.css` & `commerce.css`)

```css
:root {
  --font-sans: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --bg-app: #FAF7F0;
  --surface-card: #FFFFFF;
  --surface-subtle: #F4F0E8;
  --surface-well: #EBE5D8;
  
  --primary: #C6A15B;
  --primary-hover: #B58F49;
  --primary-light: #F7F1E3;
  --on-primary: #26211A;
  
  --text-primary: #26211A;
  --text-secondary: #5C564D;
  --text-muted: #8C8479;
  
  --border: #E5DEC9;
  --border-subtle: #EFE9DB;
  
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --radius-xl: 20px;
  --radius-2xl: 24px;
  --radius-pill: 9999px;
  
  --shadow-sm: 0 2px 8px rgba(38, 33, 26, 0.04);
  --shadow-md: 0 6px 20px rgba(38, 33, 26, 0.07);
  --shadow-lg: 0 12px 36px rgba(38, 33, 26, 0.11);
}
```

---

## 6. Tài Khoản Người Dùng & Hồ Sơ Hình Thể (`/account`, `/account/body-profile`)

### 6.1 Xác Thực & Phiên Bảo Mật (HttpOnly Session)
- **Modal Xác thực Toàn cục (`AuthModal`)**:
  - Tích hợp 2 tab Đăng nhập & Tạo tài khoản, bo góc 24px, cân giữa trên desktop và chuyển thành Bottom Sheet trên di động.
  - Hỗ trợ lưu trữ phiên bằng HttpOnly cookie từ backend (`morph_session`), tuyệt đối không lưu token/mật khẩu trong `localStorage`.
  - Khóa tạm thời 5 phút sau 5 lần thử đăng nhập sai (HTTP 429 lockout) với cảnh báo nổi bật.
  - Hỗ trợ hành động chờ (Pending Action): cho phép khách quét scan xong rồi mới đăng nhập, hệ thống tự động gắn và lưu kết quả scan vào tài khoản mà không yêu cầu quét lại.
- **Thanh Điều Khiển & Menu Header**:
  - Badge người dùng với avatar viết tắt họ tên, dropdown menu căn lề phải chống tràn mép dẫn tới Hồ sơ và Đăng xuất.

### 6.2 Hồ Sơ Hình Thể & Biểu Đồ Số Đo (`/account/body-profile`)
- **Hero Card Số Đo Gần Nhất**:
  - Hiển thị đầy đủ Chiều cao, Vòng ngực, Vòng eo, Vòng mông, Rộng vai kèm nhãn nguồn số đo rõ ràng (`user_input`, `photo_estimate`, `photo_with_prior`, `template_model`).
  - Ghi nhận chính xác ngày giờ chụp (`captured_at`) và ngày giờ bấm lưu (`saved_at`), tuyệt đối không ghép nối số đo từ các ngày khác nhau.
  - Đối với quét thân trên (`upper_body`), vòng mông được hiển thị minh bạch `Chưa đo (Thân trên)` / `Theo mẫu 3D`.
- **Biểu Đồ Biến Thiên SVG Thuần (`BodyChart`)**:
  - Đồ thị đường SVG tương tác mượt mà, không phụ thuộc thư viện ngoài, tương thích React 19.
  - Trục X: Thời gian scan thực tế. Trục Y: Số đo (cm).
  - 4 metric với màu sắc tương phản cao và ký hiệu hình học: Ngực (●), Eo (■), Mông (◆), Vai (▲).
  - Lọc khoảng thời gian 30 ngày, 90 ngày, Toàn bộ.
  - Xử lý trung thực: Dữ liệu thiếu (`null`) hoặc xuất phát từ `template_model` tạo khoảng trống ngắt quãng trên đường đồ thị; không vẽ về 0; không nội suy số đo giả.
  - Bảng dữ liệu tương đương (Accessible Table) bên dưới phục vụ đọc số đo nhanh và hỗ trợ trợ năng.
  - Chú thích công nghệ bắt buộc đi kèm biểu đồ.

### 6.3 Lịch Sử & So Sánh Số Đo (`ScanCompareModal`)
- Danh sách lịch sử scan cho phép chỉnh sửa ghi chú cá nhân, xem chi tiết, và xóa có xác nhận.
- Cho phép chọn 2 lần scan bất kỳ để mở công cụ đối chiếu Trước / Sau:
  - Bảng so sánh từng số đo với chênh lệch có dấu (`+1.5 cm`, `-0.8 cm`).
  - Cảnh báo không tương thích rõ ràng khi khác chế độ chụp (`upper_body` vs `full_body`).
  - Câu nhận định toán học trung tính, không suy đoán thể trạng hay sức khỏe.

