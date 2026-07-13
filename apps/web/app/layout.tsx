import type { Metadata } from "next";
import "./global.css";

export const metadata: Metadata = {
  title: "Incident Commander AI",
  description: "Dashboard for Incident Commander AI",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

