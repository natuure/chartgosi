import type { Metadata } from "next";
import { AuthSessionSync } from "@/components/auth-session-sync";
import "./globals.css";

export const metadata: Metadata = {
  title: "차트고시",
  description: "과거 차트를 보고 다음 5봉을 예측하는 차트 학습 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full">
        <AuthSessionSync />
        {children}
      </body>
    </html>
  );
}
