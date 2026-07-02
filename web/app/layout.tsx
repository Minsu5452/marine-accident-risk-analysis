import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "연안 해양사고 위험 지도",
  description:
    "2018–2025년 해양사고(MTIS)와 연안 해양기상(NMPNT)을 결합한 격자×시간 위험도 지도. 격자를 고르면 위험을 높인 기상 근거를 함께 확인합니다. 실제 분석 실행 결과를 키 없이 재생하는 정적 데모.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
