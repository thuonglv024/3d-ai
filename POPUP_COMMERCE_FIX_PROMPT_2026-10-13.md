# MORPH — nghiệm thu popup, ảnh thật, auth, wishlist và UI

Ngày: 13/10/2026. Source chuẩn: `D:\MORPH-AI`.

Tài liệu này là kết quả kiểm tra và prompt giao việc. Lượt kiểm tra không thay source ứng dụng hoặc dữ liệu SQLite. Source/server có thay đổi trong lúc kiểm tra; agent thực thi cần tái hiện trên phiên bản mới nhất, không áp dụng kết luận cũ một cách máy móc.

## 1. Bằng chứng kiểm tra

| Phát hiện | Bằng chứng / phạm vi | Mức độ |
|---|---|---|
| Menu camera chưa đồng bộ | Ảnh người dùng + `frontend/components/shop/CaptureSession.tsx`: camera còn là native `<select>`. CSS bo góc trigger không kiểm soát được menu OS. `FitExperience.tsx` và trang cart cũng còn select native. Không bật webcam thật trong lượt audit. | P2 |
| Popup sản phẩm mobile bị cắt nghiêm trọng | Live `/scan`, viewport 390×844: popup cao 540px, top khoảng -412px, bottom khoảng 128px dù scrollY=0. Phần search và phần lớn danh sách nằm ngoài viewport. Popup fixed nằm trong header có `backdrop-filter: blur(12px)`; cần xử lý containing block, không chỉ tăng z-index. | P1 |
| Popup sản phẩm mất focus sau Escape | Live desktop: mở picker → search có focus → Escape → dialog biến mất nhưng activeElement về body. Mobile sheet không khóa cuộn nền, không có nút đóng chuyên dụng. | P2 |
| Dropdown bộ lọc thiếu điều khiển mũi tên | Live: mở Khoảng giá → ArrowDown ở trigger vẫn giữ focus tại trigger. Source tự gán listbox/option nhưng thiếu keyboard navigation tương ứng. Các select `sr-only` phía sau đã có aria-hidden và tabIndex=-1; không báo nhầm chúng là select lộ ra. | P2 |
| Dialog lịch sử scan tách khỏi nền tảng overlay chung | Source `ScanCompareModal.tsx`: div dialog không có accessible name, Escape/focus trap/restore/scroll lock. Xóa scan và sửa ghi chú ở account body-profile dùng div backdrop tự viết, thiếu semantics và quản lý focus. Chỉ audit source, chưa thao tác tài khoản thật. | P1/P2 |
| Auth chưa có lỗi tại từng trường | Live `/auth/login`: submit rỗng chỉ hiện banner “Vui lòng điền đầy đủ email và mật khẩu.”. `/auth/register`: submit cả bốn trường rỗng chỉ báo thiếu tên. Không input nào có aria-invalid=true, focus còn ở submit. Auth đã là page riêng, không cần tạo lại route. | P2 |
| Nút hiện mật khẩu bị bỏ khỏi Tab order | Source auth login/register dùng tabIndex=-1 cho nút hiện mật khẩu. | P2 |
| Wishlist không có lối đặt hàng | Live thêm một sản phẩm thử: popup chỉ có “Xem chi tiết & chọn size” và bỏ lưu. Đã bỏ lưu lại sản phẩm thử, phục hồi danh sách ban đầu. Source chưa có chọn variant/quantity hay CTA checkout. | P1 theo yêu cầu sản phẩm |
| Wishlist có thể hiển thị rỗng giả | Source `WishlistDrawer.tsx` không có trạng thái loading/error riêng; resolver silently bỏ ID không tải được. Số item resolved khác số ID đã lưu. Cần kiểm thử lỗi mạng bằng fixture. | P2 |
| Ảnh thật vẫn gán sai sản phẩm | Mở trực tiếp hai asset hiện tại của slug `ao-blazer-dang-rong-2-hang-khuy`: ảnh chính là áo phao hồng không tay; ảnh detail là áo sơ mi khaki. Không phải blazer 2 hàng khuy và không cùng một món đồ. Đây là ảnh hiện tại trên đĩa, khác ảnh hoạt hình người dùng đã chụp trước đó. | P1 |
| Pipeline ảnh kiểm chứng sai chất lượng | `backend/scripts/curate_fashion_catalog.py` chọn hai file đầu chưa dùng trong cùng category làm primary/detail; không chứng minh cùng item, màu, giới tính/độ tuổi, chất liệu. Audit SHA-256 vẫn in “100% UNIQUE REAL PHOTOS” chỉ từ số lượng/hash, không chứng minh ảnh thật hoặc đúng sản phẩm. Chạy lại không tái sử dụng mapping cũ, có thể đổi ảnh tiếp. | P1 |
| SQLite đã có catalog ảnh | Đọc read-only `.runtime/orders.db`: 160 products, 320 product_images. Bảng product_images có id, product_id, url, alt, color_name, display_order, is_primary. SQLite lưu đường dẫn/metadata; không cần nhét binary ảnh vào DB. | Thông tin |
| Navbar và entrance animation | Source `.shop-header` chưa có bo góc; ProductCard chỉ có hover transform/zoom, không có animation xuất hiện khi vào viewport. | P2 |
| Checkout focus lỗi lần submit đầu | Source `app/checkout/page.tsx`: validateForm gọi setErrors rồi phần focus đọc errors cũ. Cần dùng kết quả validation vừa tính để focus trường đầu tiên. Chưa tạo order trong audit. | P2 |

Điểm đã đạt trong phạm vi thử: wishlist và bảng size desktop căn giữa, nền kem/bo góc; Escape trả focus đúng về trigger. Bảng size và sheet bộ lọc mobile 390×844 nằm trong viewport và có cuộn nội dung. Không nên viết lại toàn bộ phần đã tốt chỉ để thay màu.

Giới hạn: chưa chạy scan camera thật; chưa login tài khoản thật, xóa scan hoặc tạo đơn; chưa chứng nhận mọi viewport/trình duyệt. Một số lần chuyển trang gặp server từ chối kết nối rồi hoạt động lại ở tab mới; không kết luận đó là lỗi business logic. Kết luận runtime ở trên dựa trên các lần thao tác thành công.

## 2. Nguồn ảnh thật đã khảo sát

- Burst/Shopify — bộ ảnh [Clothing & Apparel](https://www.shopify.com/stock-photos/clothes), phù hợp tìm packshot và ảnh người mặc. [Ví dụ ảnh detail áo thun trắng](https://www.shopify.com/stock-photos/photos/white-t-shirt-detail), [ví dụ váy xanh](https://www.shopify.com/stock-photos/photos/strappy-dress-in-blue). Đây là nguồn ứng viên, chưa phải mapping đã duyệt cho catalog.
- [Giấy phép Burst](https://www.shopify.com/stock-photos/licenses/shopify-some-rights-reserved) cho phép sử dụng thương mại và phi thương mại theo điều kiện công bố; ghi nguồn và giấy phép từng ảnh trong manifest.
- Pexels: [giấy phép chính thức](https://www.pexels.com/license/), [giải thích sử dụng thương mại](https://help.pexels.com/hc/en-us/articles/360042295214-Can-I-use-the-photos-and-videos-for-a-commercial-project). Dùng bổ sung khi ảnh thật đúng garment và đủ độ phân giải.
- Unsplash: [giấy phép chính thức](https://unsplash.com/license). Phân biệt ảnh miễn phí với nội dung cần license riêng; nếu dùng API, tuân thủ điều kiện API tương ứng, không mặc định license ảnh thay thế mọi điều kiện API.

Không mặc định dataset phân loại quần áo trong `.cache` là catalog thương mại chất lượng cao. Cần kiểm tra quyền từng nguồn, ảnh gốc, kích thước và độ đúng sản phẩm. Không lấy ảnh trên website nhãn hàng chỉ vì tải được. Không dùng ảnh hoạt hình/AI thay cho yêu cầu ảnh chụp thật.

---

## 3. PROMPT GIAO CHO AGENT THỰC THI — sao chép từ đây

Bạn là lead engineer thực thi nâng cấp MORPH tại `D:\MORPH-AI`, với frontend và backend riêng. Hãy sửa code và dữ liệu thật trong môi trường local, kiểm thử rồi bàn giao; không chỉ viết kế hoạch. Đọc AGENTS.md và các handoff liên quan; kiểm tra diff hiện có để giữ thay đổi của agent khác. Dùng báo cáo ở phần 1 làm đầu vào, tái hiện lại trước khi sửa vì source đang thay đổi.

Mục tiêu: storefront vàng gold/nền ivory nhất quán, ảnh chụp sản phẩm thật đúng mặt hàng, auth có lỗi required inline, wishlist mua được qua checkout/order hiện có, navbar mềm mại, card xuất hiện có animation và popup/dropdown ổn định trên mobile/desktop. Không tích hợp thanh toán.

### A. Bắt buộc làm việc song song

Chốt ngắn contract asset/variant/checkout và quyền sửa file trước. Sau đó khởi chạy các sub-agent ngay, không chờ BE hoàn thành mới giao FE. Với 4 slot tổng cộng, dùng 3 sub-agent + lead:

1. **Agent A — Media + SQLite + API**: nguồn ảnh, curated manifest, migration/import, API media/variant nếu thiếu. Sở hữu backend, script media, manifest và asset sản phẩm. Là writer duy nhất cho SQLite.
2. **Agent B — Auth**: login/register pages, field errors, password toggle accessibility, auth CSS và test liên quan. Giữ routes và continuation đang có.
3. **Agent C — Wishlist + Checkout**: chọn item/variant/quantity, chuyển checkout, trạng thái loading/error, sửa focus lỗi checkout, test luồng order. Dùng fixture theo contract khi A còn làm BE.
4. **Lead — UI/overlay + tích hợp**: navbar, card entrance, shared Select/Popover/Dialog, popup picker/mobile và dialog lịch sử; quản lý CSS chung, review và E2E cuối.

Không để nhiều agent sửa cùng `commerce.css`, shared types hoặc context một lúc. Lead là owner CSS chung/shared overlay; B/C dùng stylesheet riêng có scope hoặc gửi patch để lead tích hợp. A/C thống nhất contract variant ngay từ đầu; không bịa tổ hợp từ mảng colors × sizes. Không tạo thread khác thay cho sub-agent. Nếu giới hạn slot, gộp công việc hợp lý và báo rõ, vẫn cho các nhánh độc lập chạy đồng thời. Chỉ migration ghi DB và kiểm thử tích hợp cuối mới cần tuần tự.

### B. Ảnh sản phẩm thật và SQLite

1. Đọc schema/database URL thực sự đang chạy; không tạo DB thứ hai vì đoán đường dẫn. DB quan sát hiện tại là `.runtime/orders.db`, bảng `product_images` lưu URL/alt/color/order/primary.
2. Lập inventory toàn bộ sản phẩm, primary, gallery, màu và ảnh fallback. Tìm nguồn thật từ Burst, Pexels, Unsplash hoặc asset được cấp quyền tương đương; dùng link khảo sát phần 2 để bắt đầu. Không lấy ảnh mannequin hoạt hình, render SVG/Pillow hoặc AI giả ảnh chụp.
3. Duyệt từng mapping: áo blazer phải là blazer; đúng màu/kiểu/cổ/tay; quần không thành váy; đồ người lớn không dùng ảnh trẻ em; không lấy chân dung thay ảnh garment. Gallery chỉ chứa cùng một item. Không ghép hai ảnh ngẫu nhiên cùng category. Nếu chỉ có một ảnh đúng, gallery một ảnh tốt hơn hai ảnh sai; crop detail phải ghi rõ là crop từ ảnh chính, không gọi là góc chụp thứ hai.
4. Không yêu cầu lấp đủ số lượng bằng ảnh sai. Lập danh sách thiếu nguồn và tiếp tục tìm; các item chưa có ảnh hợp lệ dùng trạng thái minh bạch, không âm thầm xóa sản phẩm/đổi tên, đổi màu để hợp thức hóa ảnh. Không báo hoàn tất 160 sản phẩm nếu chưa duyệt đủ.
5. Manifest ổn định theo product_id/slug và color_name, có source page URL, photographer/provider, license URL, ngày truy cập, source asset ID, đường dẫn local hoặc hosting phù hợp nguồn, kích thước ảnh gốc, checksum và trạng thái visual_review. Không chỉ lưu filename vô nghĩa từ dataset.
6. Chuẩn hóa ảnh theo khung 3:4 bằng contain/padding/crop đã duyệt, không cắt mất quần áo; giữ màu thật. Ảnh gốc đủ chi tiết cho PDP, không upscale ảnh nhỏ rồi gọi là high resolution. Tạo kích cỡ thumbnail/PDP phù hợp và tối ưu dung lượng; tránh tải ảnh lớn toàn bộ 160 card ngay đầu.
7. Backup SQLite bằng cơ chế snapshot an toàn khi server chạy, backup manifest/asset mapping cũ. Import có dry-run, transaction, upsert ổn định, rollback và báo cáo affected rows. Giữ product_id, variant_id, SKU, giá, tồn kho, user, order, scan. Chỉ một writer; không reset/reseed toàn DB. Chạy hai lần không tăng số dòng hoặc thay ảnh ngẫu nhiên. Cập nhật seed để restart không hồi lại ảnh hoạt hình.
8. Sau import, kiểm tra API thực trả đường dẫn mới, load HTTP 200/MIME đúng, primary duy nhất mỗi sản phẩm, thứ tự gallery/color mapping đúng, frontend card/PDP/cart/wishlist/scan picker nhất quán. Nếu dùng cache/versioned URL, invalidation phải hoạt động sau thay ảnh.
9. Kiểm tra hash chính xác và perceptual hash để phát hiện ảnh trùng/crop lại ở nhiều sản phẩm, rồi duyệt visual contact sheet theo category. Không đánh đồng hash khác nhau với ảnh thật/đúng garment. Báo cáo riêng: missing, duplicate source, near-duplicate, wrong category/color, inconsistent gallery, low-resolution. Loại bỏ tuyên bố “100% REAL” từ kiểm tra chỉ hash/size.

### C. Form login/register — lỗi rỗng tại từng input

Giữ `/auth/login`, `/auth/register`; không quay về popup. Giữ returnTo an toàn, giỏ hàng, product context, intent lưu scan và session hiện tại.

- Submit rỗng phải hiện đồng thời lỗi đỏ dưới tất cả trường bắt buộc: email/password trên login; tên/email/password/confirm password trên register.
- Có viền/icon lỗi vừa đủ, `aria-invalid`, `aria-describedby` trỏ message ID; focus và scroll tới trường lỗi đầu tiên. Không chỉ toast hoặc banner đầu form.
- Yêu cầu frontend mới chỉ là kiểm tra rỗng/whitespace-only, không thêm regex email, strength meter, business rule hay quy tắc giá trị mới. Không trim/biến đổi mật khẩu thực tế gửi server. Giữ validation và bảo mật backend; lỗi server về giá trị/credentials vẫn hiển thị rõ, không giả thành thành công.
- Nếu cần tắt browser validation tooltip để thống nhất message inline thì dùng noValidate và tự quản lý required; không để tooltip native che trải nghiệm.
- Sau lần submit đầu hoặc blur, cập nhật/xóa lỗi riêng trường đang sửa; không xóa lỗi các trường khác. Submit Enter hoạt động. Ngăn double submit trong request. Loading/error/network failure phải phục hồi được.
- Nút hiện mật khẩu phải tab tới được, type=button, label đổi theo trạng thái; giữ autocomplete đúng.
- Sửa copy “chuẩn xác”, “may đo”, “riêng tư tuyệt đối” thành diễn đạt trung thực với engine ước lượng đang có; tránh đưa chi tiết cookie kỹ thuật vào nội dung marketing.

### D. Wishlist → Checkout → Order, không thanh toán

Không chỉ thêm link `/checkout` khi wishlist chưa có size/màu. Thực hiện:

1. Wishlist có loading skeleton, error/retry, empty state thật và dòng unavailable. Giữ ID yêu thích khi API lỗi; badge và nội dung giải thích đúng số item.
2. Cho chọn một hoặc nhiều item muốn mua, chọn màu, size, số lượng theo exact variant còn tồn. Chưa chọn variant thì báo lỗi inline; không tự chọn size M/L hoặc màu đầu tiên. Gợi ý size nếu có chỉ là đề xuất, người dùng được chọn lại.
3. CTA rõ “Thêm vào giỏ” và/hoặc “Tiếp tục đặt hàng”. Với CTA thứ hai: thêm những variant đã chọn vào giỏ hiện có, giữ các món cũ, hiển thị rõ checkout sẽ gồm cả giỏ. Chỉ chuyển `/checkout` sau khi state cập nhật thành công. Không ghi đè/xóa giỏ, không xóa wishlist tự động. Nếu thiết kế chọn mua riêng thì dùng draft tách biệt, không phá giỏ hiện tại.
4. Backend kiểm tra variant/tồn kho/giá qua quote hoặc cơ chế đang có; xử lý thay đổi giá, hết hàng, stale variant, lỗi mạng. Không tin tổng tiền do FE gửi. Tránh tạo item/đơn trùng khi click liên tục.
5. Trang `/checkout` nhập thông tin giao nhận → xem lại → xác nhận đặt hàng → `/orders/[id]` của đơn mới. Không có payment gateway hoặc giả trạng thái đã thanh toán. Giữ giỏ nếu đặt hàng thất bại; xử lý reload/Back theo cơ chế chống tạo đơn trùng hiện có.
6. Sửa validation checkout: tính nextErrors và trả về ngay, setErrors rồi focus từ nextErrors; không đọc state cũ ngay sau setState.
7. Test guest và signed-in khi hệ thống hỗ trợ, refresh/Back/login continuation, wishlist→cart→checkout, giỏ sẵn có, hết hàng, item bị gỡ. Dùng dữ liệu thử; không tạo/xóa dữ liệu cá nhân để nghiệm thu.

### E. Navbar mềm mại và animation card

- Navbar desktop dạng thanh inset bo góc 20–24px, margin hợp lý, nền ivory, viền gold nhạt và shadow nhẹ; giữ tổng chiều cao gọn, sticky không che nội dung. Mobile có layout compact, logo/actions không chen lấn. Đồng bộ storefront và scan bằng token, không đổi toàn bộ nền sang vàng đậm.
- Không đặt overflow:hidden lên ancestor của dropdown chỉ để bo góc; không tạo containing block làm sheet fixed bị neo vào header. Kiểm tra blur/transform/sticky với overlay.
- Entrance card: fade + translateY khoảng 12–20px, 240–360ms, stagger khoảng 40–60ms theo batch viewport, giới hạn tổng delay. Dùng CSS/IntersectionObserver hoặc thư viện sẵn có hợp lý. Không chờ tất cả ảnh tải xong; giữ aspect-ratio, không layout shift.
- SSR/no-JS vẫn thấy sản phẩm; không để opacity:0 vô thời hạn. prefers-reduced-motion hiển thị ngay; animation chạy một lần khi vào viewport, pagination/filter chỉ animate item mới, thao tác wishlist/variant không nhấp nháy lại cả grid. Không áp animation width/height/top gây reflow mỗi frame.

### F. Popup/dropdown còn lại — sửa cùng đợt

- Inventory các overlay reachable: camera device, capture framing, cart variant, filter/sort, product picker, menu account/mobile nav, wishlist, size chart, scan result settings, compare scans, delete scan, edit note và các confirmation còn lại. Phân biệt legacy component không còn được mount; không sửa file chết để tuyên bố đã sửa luồng thật.
- Xây/reuse primitive riêng cho Select/Combobox, Popover/Menu, Dialog/AlertDialog. Chung typography/token ivory-gold, border/radius/shadow/focus, option selected/disabled/loading/empty. Không ép tất cả cùng kích thước hoặc thành modal.
- Camera select native trong screenshot cần UI listbox/combobox accessible nếu muốn menu đồng nhất; không chữa bằng CSS option hoặc z-index đơn thuần. Mở/đóng menu không restart stream; đổi camera mới đổi stream; khóa lựa chọn đúng phase countdown/capture. Không thay flow auto chính diện → xoay 90° → countdown → nghiêng.
- Desktop popover neo theo trigger, collision/flip/shift khi sát mép; mobile picker là sheet bottom nằm trong viewport, có title/nút đóng/backdrop, safe area và scroll region. Fix tình trạng top=-412px ở 390×844. Không để header blur/transform chứa sheet fixed; portal phải chọn đúng host.
- Không portal mọi thứ mù quáng vào document.body: menu trong native dialog top layer hoặc fullscreen camera phải nằm trong host phù hợp, không rơi sau dialog hay biến mất khi fullscreen.
- Keyboard: Enter/Space mở, ArrowUp/Down + Home/End điều hướng listbox, Enter chọn, Escape chỉ đóng layer trên cùng, trả focus trigger hợp lệ. Tab theo semantics đúng; modal trap focus + nền inert; nonmodal popover không trap tùy tiện. Tabs cần keyboard behavior đúng hoặc dùng buttons/filter semantics phù hợp.
- Chung overlay manager/scroll lock có tính đến nhiều layer; tránh Modal và useDrawerA11y mỗi nơi tự restore overflow khác nhau. Khi đóng overlay con, parent vẫn khóa nền; đóng hết thì scroll/focus phục hồi. Không làm một Escape đóng cả dropdown và dialog cha.
- Migrate compare/delete/note sang primitives chung. Confirm xóa dùng AlertDialog, focus mặc định ở Hủy; lỗi API giữ nội dung và cho retry; không tự thực thi xóa. Note có label, dirty-state phù hợp, không mất bản nháp ngoài ý muốn.
- Auth và cart là pages, không tạo lại AuthModal/CartDrawer để xử lý yêu cầu này. Giữ phần size chart/wishlist đang tốt, bổ sung behavior chung và test regression.

### G. Nghiệm thu có bằng chứng

Tối thiểu kiểm tra desktop 1440×900, laptop 1366×768, tablet 820px, mobile 390×844 và 360px; zoom 200%, bàn phím và reduced motion. Nếu không có trình duyệt/thiết bị thì ghi chưa thử, không đánh dấu pass.

- Auth: submit tất cả rỗng; thiếu riêng từng trường; whitespace-only; sửa một trường; Enter; show/hide password bằng Tab; server/network error; auth continuation. Required message đỏ dưới đúng trường và focus trường đầu.
- Media: đọc DB/API sau import; mapping các item/variant; gallery cùng garment; check toàn catalog bằng contact sheet và mở từng case nghi ngờ; không ảnh hoạt hình, không chân dung không liên quan, không dùng ảnh món khác làm detail. Dry-run/import lần 2 không phát sinh duplicate.
- Wishlist: zero/one/many/unresolved, load fail/retry, chọn variant hợp lệ/hết hàng, đi checkout có giỏ cũ, refresh và đặt một đơn demo thành công; lỗi không xóa giỏ/nhân đôi đơn.
- Popup: mouse/touch/keyboard, Escape/Tab/Shift+Tab, focus restore, click-outside, sát mép viewport, scroll, resize, nested modal, camera mở rộng, labels thiết bị dài/0–1–n devices. Fake camera fixtures cho automated tests phải được ghi rõ là giả; không giả chứng minh scan AI chính xác trên người thật.
- UI: screenshots navbar/card/popup desktop/mobile, video hoặc chuỗi ảnh ngắn chứng minh entrance animation; static screenshot không đủ chứng minh motion. Không overflow ngang, không CTA ngoài viewport, không card biến mất khi reduced motion/no JS.
- Chạy typecheck/build và test liên quan auth/catalog/orders; ghi command, pass/fail và lỗi còn lại. Test hành vi, không chỉ kiểm tra className hoặc snapshot tự khớp implementation.

Deliverables: code đã tích hợp; manifest nguồn ảnh + migration/import/rollback; audit before/after theo từng item; báo cáo thay đổi DB số dòng nhưng không dump dữ liệu user; ảnh/video nghiệm thu; cập nhật handoff. Không báo “hoàn tất” chỉ vì build xanh, hash ảnh khác nhau hoặc UI đẹp khi chưa test luồng thực.
