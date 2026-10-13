# MORPH — Kết quả kiểm tra trực tiếp và prompt sửa lỗi

Ngày kiểm tra: 13/10/2026. Source: `D:\MORPH-AI`. Frontend `http://127.0.0.1:3000`, backend `http://127.0.0.1:8000` đều truy cập được.

## Kết quả có bằng chứng

| Mức độ | Phát hiện | Bằng chứng / vị trí |
|---|---|---|
| P1 | Ảnh trùng nội dung dù khác tên file | 160 sản phẩm/API, 160 URL ảnh chính, chỉ 95 SHA-256 khác nhau; 36 nhóm trùng chính xác bao gồm 101 sản phẩm. Không có ảnh chính thiếu file cục bộ. Chưa tính ảnh gần giống sau chỉnh màu/crop. |
| P1 | Ảnh không thể hiện đúng sản phẩm | Ảnh người mặc suit xanh gắn với blazer có màu gốc ghi Đen than; ảnh chân dung xuất hiện trên các thẻ áo thun trong ảnh người dùng. Script `backend/scripts/generate_product_images.py` chọn một bộ ảnh gốc theo từ khóa, chỉnh sáng/phủ màu toàn ảnh và crop để tạo ảnh detail; không tạo thiết kế trang phục mới. |
| P1 | Bộ lọc giá không được backend áp dụng | Qua proxy FE: `priceRange=under-500` và `maxPrice=500000` vẫn trả total=160, có sản phẩm 1.350.000đ trong kết quả; `max_price=499999` trả 34 sản phẩm, tối đa 490.000đ. FE/BE khác tên tham số. |
| P1 | Bộ lọc nhóm màu trả rỗng sai | `color=trắng`, `đen`, `xanh`, `nâu`, `be` đều trả 0; `Trắng ngà` trả 16, `Đen than` trả 13. UI gửi nhóm màu, DB so sánh tên màu chính xác. Đã tái hiện Trắng/Kem trên mobile. |
| P1 | Scan product picker chỉ có 22/160 sản phẩm | UI hiện Tất cả (22); `fetchProducts({limit:200})` trong `ProductPickerPopover.tsx`; BE `le=100`. Gọi cả cổng 3000/8000 với limit=200 đều 422, FE âm thầm fallback catalog tĩnh. |
| P1 | Wishlist báo có 1 nhưng mở popup trống | Lưu Áo Blazer Dáng Rộng 2 Hàng Khuy: header (1), popup (0). `WishlistDrawer.tsx` resolve qua getAllProducts tĩnh. |
| P1 | Không đổi được biến thể sản phẩm mới trong giỏ | PDP blazer có 2 màu, 4 size. Thêm Be sáng/M: cart combobox chỉ có Be sáng và M. `app/cart/page.tsx` lookup catalog tĩnh. |
| P1 | Header tablet tràn ngang | Viewport 820px, document.scrollWidth=1171; search/account/wishlist/cart ra ngoài viewport. Desktop navigation chỉ ẩn tại <=768px. |
| P2 | Thứ tự size sai | API và UI hiển thị L, M, S, XL; các áo khác L, M, S, XL, XS. Không theo thứ tự kích cỡ. |
| P2 | Gallery giả góc nhìn bổ sung | Ảnh detail được crop/phóng to ảnh chính, UI gọi “Góc nhìn 2”. Cần đúng góc chụp hoặc ghi rõ ảnh phóng to. |
| P2 | Related products lệch nguồn dữ liệu | Xem blazer mới, mục related dùng các áo thun đầu catalog tĩnh. Cần truy vấn dữ liệu hiện hành với quy tắc liên quan rõ ràng. |
| P2 | Filter mobile có nút Áp dụng nhưng thay đổi có hiệu lực trước khi bấm | Chọn Trắng/Kem rồi đóng bằng X: danh sách nền đã trở thành 0. Chọn mô hình áp dụng tức thì hoặc draft/apply nhất quán. |
| P1 — đã nằm trong prompt trước | Quần chưa có hint full-body sớm | Chọn Quần tây Xếp ly Dáng rộng trong /scan: vẫn mặc định upper_body và hướng dẫn “không cần thấy chân”, chưa có hint riêng cho quần trước khi bật camera. |
| P1/P2 — source còn tồn tại | Các lỗi commerce đã báo trước | Checkout vẫn fallback quote; FE gửi notes/BE nhận note; clearCart toàn bộ; idempotency key theo mount, chưa fingerprint; orders validate màu/size rời rạc, chưa kiểm tra/trừ tồn kho. Đã kiểm tra lại source, không tạo đơn trên database đang chạy. |

### Kiểm thử đã thực hiện và giới hạn

- Kiểm tra browser: storefront, PDP, wishlist, cart, checkout không submit, scan onboarding/product picker, popup filter và login; viewport desktop 1366, tablet 820, mobile 390.
- Đọc catalog API cả 160 sản phẩm; hash ảnh chính cục bộ; đọc source generator, seed, frontend/backend contracts.
- TypeScript: `tsc --noEmit --incremental false` PASS.
- Backend: `test_orders.py`, `test_catalog_db.py`, `test_auth_and_history.py`: **29 passed**, 1 deprecation warning. Chạy trong subprocess, database và scan artifact tạm được cấu hình trước import app.
- Popup wishlist desktop đã nằm giữa; filter/login mobile hiển thị dạng sheet; mobile storefront 390px không tràn ngang ở trạng thái được kiểm tra. Không nên báo tất cả popup đều hỏng.
- Chưa bật camera thật, chưa scan cơ thể, chưa nghiệm thu số đo/recommendation thực tế. Chưa đăng nhập tài khoản thật hoặc kiểm tra chart có dữ liệu cá nhân trong browser. Test auth/history không thay thế E2E thực tế.
- Kiểm tra ảnh trước đây ở `verification/scripts/product-images-verification.cjs` chủ yếu kiểm tra naturalWidth > 0; điều đó không chứng minh đúng sản phẩm hay không trùng ảnh.

## PROMPT GỬI AGENT TRIỂN KHAI

Bạn là agent điều phối sửa MORPH AI tại `D:\MORPH-AI`. Đọc toàn bộ báo cáo phía trên và source hiện tại trước khi code. Frontend/backend đang chạy ở 3000/8000. Mục tiêu là sửa các lỗi đã tái hiện, ưu tiên catalog đúng hình và flow hoạt động thật. Không dừng ở kế hoạch hoặc chỉ đổi CSS.

### 1. Chạy các subagent song song thực sự

Đọc AGENTS.md, frontend/AGENTS.md, DESIGN.md và handoff hiện hành. Chốt nhanh contract sản phẩm/ảnh/filter/variant/quote cùng quyền sở hữu file, rồi khởi chạy đồng thời:

- Agent A — Catalog media: inventory toàn bộ ảnh, sửa pipeline ảnh, tạo/chuẩn bị bộ ảnh phù hợp từng sản phẩm, asset manifest và kiểm tra trùng. Sở hữu thư mục ảnh và script media, không tự ghi DB đang chạy.
- Agent B — Backend/data: catalog/filter/pagination, migration/seed, biến thể/tồn kho/quote/order và test backend; phối hợp contract session/auth và lưu scan sau đăng nhập tại mục 8. Là owner duy nhất của schema và thao tác cập nhật DB.
- Agent C — Frontend: thống nhất API data source, wishlist/cart/picker, gallery/filter, checkout, responsive/accessibility; sở hữu trang /auth/login, /auth/register, AuthContext và các điểm điều hướng auth tại mục 8.
- Agent điều phối: contract, quản lý phạm vi, tích hợp task auth/chart/size trước, review và E2E.

Khởi chạy A/B/C trước khi chờ bất kỳ agent nào hoàn tất. FE dùng contract/fixture trong khi BE làm; media chạy độc lập. Không thực hiện A xong rồi mới B rồi mới C. Các file dùng chung chỉ có một owner; trao đổi yêu cầu thay vì ghi đè nhau. Nếu nền tảng không hỗ trợ subagent, nói rõ, không giả vờ đã chạy song song.

### 2. Sửa tận gốc ảnh catalog

- Tạo inventory toàn bộ 160 sản phẩm và các ảnh gallery: product ID, URL, kích thước, byte size, SHA-256, perceptual hash, ảnh chính/phụ, source/provenance, màu, trạng thái duyệt.
- Phân biệt trùng file chính xác với gần giống do crop, mirror, đổi sáng/màu/viền. Perceptual hash để gắn cờ review, không tự động kết luận hai trang phục giống nhau chỉ vì nền studio giống.
- Không dùng 22 ảnh gốc xoay vòng cho 160 tên sản phẩm. Không đổi filename/query string, crop, lật hoặc phủ màu để lách kiểm tra uniqueness.
- Thay các ảnh sai bằng ảnh hợp lệ có quyền sử dụng hoặc ảnh AI minh họa được ghi nguồn. Nếu tạo ảnh AI, dùng công cụ image generation theo skill hiện có; không vẽ giả ảnh sản phẩm bằng script rồi gọi đó là ảnh chụp thật.
- Mỗi thiết kế khác nhau phải có hình thể hiện đúng kiểu dáng: áo thun, polo, tay dài, sơ mi, blazer, quần, chân váy, đầm. Không dùng chân dung cận mặt làm ảnh chính áo; không dùng suit cho cardigan/poncho; không dùng quần dài cho quần short.
- Đối chiếu tên, hình, họa tiết, độ dài tay/ống, màu và mô tả. Với catalog demo, nếu thay nội dung cho phù hợp ảnh thì cập nhật có chủ đích toàn bộ thuộc tính liên quan; không đổi tên hàng loạt để che lỗi ảnh.
- Giữ >=150 sản phẩm như yêu cầu catalog đã có. Không âm thầm xóa/ẩn phần lớn sản phẩm để đạt tỷ lệ ảnh đẹp. Không sửa product ID/slug làm hỏng wishlist, cart, lịch sử đơn hoặc liên kết scan.
- Một ảnh đúng tốt hơn nhiều ảnh sai. Gallery phải cùng một thiết kế; crop ảnh chính chỉ được gọi là phóng to, không gọi góc sau/góc thứ hai độc lập.
- Ảnh theo màu dùng mapping rõ ràng. Nếu màu chưa có ảnh, hiển thị thông báo chính xác về màu ảnh đang xem; không gán tên Đen than cho ảnh suit xanh.
- Giữ tỷ lệ card nhất quán, thể hiện đầy đủ trang phục, nền không đổ màu lấy từ một pixel ngẫu nhiên. Tối ưu kích thước và loading, không bóp méo/cắt mất phần nhận diện sản phẩm.
- Thiếu/lỗi ảnh dùng placeholder trung tính. Không fallback sang ảnh món hàng khác.
- Pipeline có dry-run, manifest/version và regenerate có chọn lọc. Không skip ảnh sai chỉ vì file đã tồn tại. Cập nhật cache bằng asset version/content hash khi nội dung thay đổi.

### 3. Đồng bộ catalog/API xuyên hệ thống

- Shop, search, scan picker, PDP, wishlist, cart, related products dùng dữ liệu SQLite qua API thống nhất. Catalog tĩnh chỉ là fixture test hoặc chế độ demo được bật rõ ràng, không âm thầm thay thế dữ liệu đang chạy.
- Sửa limit=200 bị 422. Picker dùng server search/pagination hợp lệ, truy cập được toàn bộ sản phẩm; không chỉ đổi sang limit=100 rồi bỏ mất 60 sản phẩm còn lại.
- Sửa tên tham số giá: min_price/max_price hoặc contract thống nhất khác. Các khoảng giá phải có ranh giới rõ, không trùng/mất sản phẩm tại 500k và 1 triệu.
- Chuẩn hóa nhóm màu bằng key/mapping, ví dụ white gồm trắng/kem; không so sánh “trắng” bằng tuyệt đối với “Trắng ngà”. FE/BE cùng semantics.
- Filter size lấy từ dữ liệu khả dụng, bao gồm 33/34/XXL nếu tồn tại. Sort size theo thang XS→S→M→L→XL→XXL; size số tăng dần, không sort alphabet.
- Kiểm tra color+size thuộc cùng biến thể khả dụng; không ghép hai điều kiện EXISTS trên hai biến thể khác nhau rồi coi là mua được.
- Wishlist đã lưu sản phẩm mới phải hiện đầy đủ; cart phải cho đổi sang các biến thể thực tế. Related products loại chính nó và áp dụng quy tắc cùng nhóm/kiểu dáng trước fallback.
- API lỗi phải phân biệt với kết quả rỗng và 404; có retry. Không hiển thị catalog cũ như dữ liệu hiện hành.
- Request cũ không ghi đè filter/search mới. URL, phân trang và Back/Forward nhất quán.

### 4. Sửa responsive và thao tác

- Sửa header vùng 769–1100px: chuyển sang menu thu gọn đúng lúc, không để account/cart nằm ngoài viewport. Không che lỗi bằng overflow-x:hidden toàn trang.
- Test 390, 768, 820, 1024, 1366, 1920px và zoom 200%. Kiểm tra các phần tử tương tác thật sự nằm trong viewport.
- Giữ gold/ivory, bo góc hiện tại. Popup desktop đặt giữa khi phù hợp; dropdown bám trigger, có xử lý mép màn hình; mobile sheet có header/footer thao tác rõ ràng. Riêng login/register phải là trang độc lập theo mục 8, không dùng popup hoặc sheet.
- Filter mobile: chọn draft+Áp dụng hoặc áp dụng tức thì. Nếu draft, X/Escape phải bỏ thay đổi chưa áp dụng; nếu tức thì, đổi nhãn nút thành “Xem kết quả”. Không để nút Áp dụng chỉ mang tính trang trí.
- Kiểm tra keyboard, focus trap/return focus, scroll lock, đóng/mở lặp lại; không phá các sửa modal đã đúng.
- Rút gọn announcement/hero mobile để danh sách mua sắm dễ tiếp cận. Đây là cải thiện UX, không được làm mất nút scan.
- Một lần thêm giỏ chỉ cần một phản hồi rõ ràng, tránh đồng thời toast và khối thông báo lặp lại.

### 5. Hoàn tất các lỗi commerce và scan còn tồn tại

- Kiểm tra lại prompt trước, sửa các lỗi còn thực tế trong source: quote lỗi không fallback giá client; quote stale chặn submit; giá đổi phải được xác nhận lại.
- Validate product/variant active, tồn kho và tổng quantity đã gộp. Tạo đơn/trừ kho trong transaction; không oversell hoặc trừ kho lại khi retry.
- Idempotency gắn payload fingerprint; cùng key khác payload trả conflict; retry sau timeout/refresh không tạo đơn mới. Chỉ xóa snapshot giỏ đã đặt, không clear sản phẩm mới thêm.
- Thống nhất note/notes, form validation và focus lỗi. Không mất draft khi quay lại giỏ trong phiên.
- Copy đúng demo chưa có thanh toán; bỏ hứa gửi SMS/email, giao hàng/COD/đổi trả nếu hệ thống chưa thực hiện hoặc chưa có chính sách được xác nhận.
- Quần/chân váy/đầm: hint full-body ngay ở bước nhập chiều cao/chọn sản phẩm; nói rõ cần thấy mông/chân để quan sát các số đo liên quan. Với laptop không đủ khung, hướng dẫn bố trí camera/thiết bị khác; không giả định tăng kích thước preview sẽ tăng góc nhìn vật lý camera.
- Giữ camera-only front→90°→countdown→process. Không thêm lại upload hay mannequin trước scan.
- Tiếp nối sửa auth/guest token, lịch sử chart và recommend size từ task trước. Không hiển thị số đo suy luận như số đo đã quan sát, không báo đủ dữ liệu cho size quần khi thiếu dữ liệu cần thiết.

### 6. Migration/seed không làm mất thay đổi đã sửa

- Seed hiện upsert lại stock/is_active và product_images. Sửa để reseed thường không phục hồi tồn kho đã bán, kích hoạt sản phẩm đã tắt hoặc ghi đè mapping ảnh đã duyệt.
- Media migration chạy transaction, có backup SQLite nhất quán và báo diff trước/sau. Không reset DB. Bảo toàn users, scans, orders và snapshot đơn cũ.
- Asset manifest là nguồn bền vững; restart/reseed không tái tạo bộ ảnh lỗi từ generator cũ.
- Không tải ảnh cá nhân/body scan lên dịch vụ tạo ảnh hoặc bên thứ ba để xử lý catalog.

### 7. Nghiệm thu có bằng chứng

- Toàn bộ catalog: kiểm tra URL ảnh, decode ảnh, exact hash và near-duplicate clusters. Xuất contact sheet có product ID/tên theo từng nhóm, duyệt hình thực tế. Không coi unique URL hay naturalWidth>0 là đủ.
- Thiết kế khác nhau không còn dùng chung nội dung ảnh chính; mọi ngoại lệ cùng product family phải được ghi rõ, không dùng ngoại lệ để giữ trùng hàng loạt.
- Các test regression bắt đúng lỗi audit: filter giá/màu có kết quả đúng, picker tìm được sản phẩm ngoài 100 đầu, wishlist sản phẩm mới hiện, cart đổi đủ variant, size đúng thứ tự.
- Test stock/idempotency/quote/notes với DB tạm trước khi import app; không chạy test có lifecycle cleanup lên artifact scan thật.
- Browser test happy path và lỗi: shop→filter→PDP→wishlist→cart→checkout→xác nhận đơn test; kiểm tra cả API và UI, không chỉ text thành công.
- Kiểm tra scan onboarding quần/đầm, preserve product context, auth/history/size ở các điểm nối. Camera thực tế chỉ được đánh dấu pass khi đã thử; fixture/mocked scan phải ghi rõ.
- Nghiệm thu đầy đủ auth routes và chuyển tiếp về flow gốc theo checklist mục 8; không còn entry point mở popup login/register.
- Chạy typecheck/build/tests; chụp desktop/tablet/mobile sau sửa. Ghi cả test fail/block, không viết báo cáo 100% pass khi chưa chạy.
- Bàn giao AUDIT_FIX_REPORT.md, ASSET_MANIFEST, thống kê duplicate trước/sau, migration/seed notes và các giới hạn còn lại.

### 8. Thay popup login/register bằng trang auth có router riêng

Đây là yêu cầu bổ sung của người dùng, không phải lỗi crash của popup hiện tại: xây trải nghiệm đăng nhập/đăng ký dạng trang hoàn chỉnh và tích hợp vào toàn hệ thống. Không chỉ chuyển nguyên modal sang giữa một trang trống, không dùng intercepted route vẫn hiển thị như popup.

**Routes và kiến trúc**

- Tạo `/auth/login` và `/auth/register`, dùng auth layout và component form chung phù hợp Next.js hiện tại. `/auth` điều hướng về `/auth/login`.
- Mỗi route có title/H1 rõ ràng, hỗ trợ truy cập trực tiếp, reload, Back/Forward và liên kết chuyển giữa đăng nhập/đăng ký.
- Tái sử dụng API auth, session/cookie và users table hiện có; không tạo hệ thống user/session thứ hai, không login giả bằng localStorage.
- Agent C làm giao diện/routing song song với Agent B kiểm tra API/session/continuation. Chốt contract sớm; không đợi backend làm xong mới bắt đầu trang auth. Agent điều phối kiểm thử các điểm nối.

**Thiết kế trang auth**

- Giữ nhận diện MORPH gold + ivory, typography và radius đồng bộ shop/scan. Desktop có vùng form dễ đọc và vùng giới thiệu ngắn về lưu số đo/lịch sử/tìm size; mobile một cột, ưu tiên form trong viewport đầu tiên.
- Header gọn gồm logo và liên kết về mua sắm. Không mang toàn bộ bộ lọc/menu shop vào trang auth. Có đường quay lại ngữ cảnh trước khi đăng nhập, không chỉ luôn về trang chủ.
- Form login: email, mật khẩu, hiện/ẩn mật khẩu, CTA “Đăng nhập”, link “Tạo tài khoản”. Form register: tên hiển thị, email, mật khẩu và xác nhận mật khẩu; nêu yêu cầu mật khẩu khớp backend, không bắt nhập số đo hay thông tin giao hàng.
- Label luôn nhìn thấy; autocomplete đúng (email, current-password, new-password); cho phép paste/password manager; Enter submit; focus-visible, error gắn với field và thông báo server dễ hiểu.
- Loading không làm nhảy layout; chặn submit trùng ở handler và nút. Lỗi vẫn giữ dữ liệu không nhạy cảm đã nhập, không bắt điền lại cả form. Không lưu password vào URL, localStorage, sessionStorage hoặc logs.
- Animation chuyển trạng thái nhẹ, tôn trọng reduced motion. Không lặp hero marketing dài hoặc thêm nhiều card lồng nhau. Tablet/mobile không tràn ngang, CTA không bị bàn phím che.
- Chỉ hiển thị chức năng thực sự hoạt động. Không tạo nút Google/Facebook, “Ghi nhớ đăng nhập”, “Quên mật khẩu” hoặc checkbox điều khoản làm cảnh nếu chưa có backend/nội dung phù hợp; không mở rộng OAuth/email recovery ngoài scope này.

**Thay toàn bộ điểm vào auth**

- Rà soát Header, menu mobile, `/account`, body-profile/chart, chi tiết scan, nút lưu scan và mọi caller của openAuthModal/AuthModal. Chuyển sang navigation helper thống nhất.
- Khách bấm tài khoản vào `/auth/login`; người đã đăng nhập vào `/account`. Protected routes chưa có session chuyển login với đích quay lại chính xác. Trong lúc kiểm tra session có loading state, không flash nội dung riêng tư rồi mới redirect.
- Sau thành công, refresh trạng thái user/session rồi quay lại `returnTo` hợp lệ; nếu không có đích thì về `/account`. Link login/register phải giữ cùng returnTo và ý định đang chờ.
- Validate returnTo là đường dẫn nội bộ cùng origin. Từ chối URL ngoài, protocol-relative URL và các dạng encode bypass; ngăn loop auth→auth. Fallback an toàn về `/account`.
- Người đã đăng nhập truy cập login/register được điều hướng hợp lý; Back không tạo vòng lặp đăng nhập. Đăng ký xong chỉ tự đăng nhập nếu API thực sự tạo session; nếu không, đưa sang login với thông báo rõ ràng, không báo đã đăng nhập giả.
- Xóa mount/import/dead code AuthModal và cơ chế pendingAction callback cũ sau khi chuyển hết caller. Không xóa primitive Modal đang được chức năng khác sử dụng. Quét toàn repo để bảo đảm không còn đường mở auth popup.

**Giữ liên tục flow mua sắm và scan**

- Ví dụ 1: PDP sản phẩm A, màu Be/size M → đăng nhập → quay lại đúng PDP A và lựa chọn còn nguyên.
- Ví dụ 2: giỏ/checkout → đăng nhập tự nguyện → quay lại đúng bước, giữ giỏ và draft người nhận. Guest checkout vẫn hoạt động; không thêm yêu cầu login bắt buộc vào mua hàng hiện tại.
- Ví dụ 3: scan hoàn tất → khách bấm “Lưu số đo” → login/register → quay lại đúng kết quả scan và sản phẩm, hoàn tất lưu đúng một lần theo ý định đã xác nhận.
- Callback JavaScript trong AuthContext không thể đại diện cho continuation qua reload. Thay bằng continuation có kiểu/allowlist (ví dụ return_to + intent save_scan + scan reference), có hạn dùng và xác minh quyền sở hữu phía server; không thực thi tùy ý action lấy từ URL.
- Không đưa guest token, ảnh, số đo, credentials hoặc dữ liệu giao hàng vào query string. Giữ quyền claim guest scan qua cơ chế bảo mật thống nhất với task auth trước, không tự sinh token FE khác token server.
- Điều hướng nội bộ và reload cần xử lý ngữ cảnh còn hiệu lực. Không giả vờ giữ được scan nếu chỉ nằm trong memory đã mất; dùng cơ chế resume phía server phù hợp contract hoặc báo phiên hết hạn rõ ràng, có CTA scan lại.
- Khi login thành công nhưng lưu scan thất bại, vẫn giữ trạng thái đã đăng nhập, thông báo lỗi lưu riêng và cho retry idempotent. Không nuốt lỗi rồi báo đã lưu thành công.
- Chỉ tiếp tục hành động người dùng đã yêu cầu; mở trang login thông thường không tự claim/lưu scan hoặc tạo đơn. Nếu hủy auth, không mất giỏ hay tự thực hiện pending action.
- Chuyển khỏi camera đang hoạt động phải dừng stream, countdown và request hướng dẫn; không giữ camera chạy ngầm trên trang auth. Không lưu raw frames để duy trì navigation.
- Logout hoặc chuyển user phải xóa state riêng tư của user cũ (scan/chart/advice/pending intent); backend vẫn kiểm tra quyền, không chỉ ẩn UI. Không xóa giỏ khách vô cớ.

**Checklist nghiệm thu auth**

- Truy cập trực tiếp/reload hai route, chuyển login↔register, Back/Forward; tất cả hiển thị page thực sự, không backdrop/modal.
- Đăng nhập đúng/sai, đăng ký email trùng, mật khẩu không khớp, API lỗi/offline và session hết hạn; thông báo chính xác, không double submit.
- Protected route → login → trở lại đúng route; returnTo ngoài origin hoặc auth-loop bị từ chối.
- Auth từ PDP, cart/checkout và save-scan không mất ngữ cảnh; reload và chuyển tab login/register vẫn xử lý continuation đúng. Scan hết TTL báo thật, không dựng kết quả giả.
- Lưu scan sau auth đúng chủ sở hữu, đúng một lần; lỗi save có retry; user B không thấy state hoặc dữ liệu user A.
- Người đã có session không bị buộc login lại; logout không báo thành công giả nếu request thất bại.
- Kiểm tra 390/820/1366px, keyboard-only, focus/error announcement, password manager và reduced motion. Chụp cả login/register desktop/mobile.
- Regression: shop/filter/cart/checkout/scan và các modal không thuộc auth vẫn hoạt động. Cập nhật handoff với routes, returnTo/continuation contract, cách test và các giới hạn chưa hỗ trợ.

Không tích hợp thanh toán, dịch vụ vận chuyển hoặc public deploy. Không sửa source cũ ở Documents/Codex. Không ghi đè thay đổi của agent khác. Hoàn thành các sửa được giao rồi mới báo kết quả.

## Bổ sung sau kiểm thử popup, auth và media

Đọc `D:\MORPH-AI\POPUP_COMMERCE_FIX_PROMPT_2026-10-13.md` cho bằng chứng mới nhất và prompt phân công song song. Auth routes hiện đã tồn tại; phần bổ sung yêu cầu cải thiện lỗi required inline, không tạo lại pages. Ảnh sản phẩm đang thay đổi: cần kiểm tra đúng garment/gallery, không chỉ hết trùng hash. Các kết luận cũ phải được tái hiện trước khi sửa.
