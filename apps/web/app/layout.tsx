import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Incident Commander AI",
  description: "Dashboard for Incident Commander AI",
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
