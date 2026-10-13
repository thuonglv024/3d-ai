import type { Metadata } from "next";
import "@fontsource/be-vietnam-pro/400.css";
import "@fontsource/be-vietnam-pro/500.css";
import "@fontsource/be-vietnam-pro/600.css";
import "@fontsource/be-vietnam-pro/700.css";
import "./globals.css";
import "./scan-review.css";
import "./commerce.css";
import "./scan-result.css";
import "./capture-flow.css";
import "./account/account.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "MORPH Studio — Một lựa chọn vừa bạn",
  description: "Cửa hàng thời trang MORPH Studio với công nghệ đối chiếu size và hình thể 3D qua webcam.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
