import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/layout/Header";

export const metadata: Metadata = {
  title: "fam Document Checker",
  description:
    "AI-powered document checker for Dubai real estate transactions. Upload property documents for automated compliance verification and approval routing.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white min-h-screen text-fam-gray font-sans">
        <Header />
        <main className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pb-12">
          {children}
        </main>
      </body>
    </html>
  );
}
