import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "차트고시",
  description: "과거 차트를 보고 다음 5봉을 예측하는 게임형 투자 학습 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
