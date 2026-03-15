import type { Metadata, Viewport } from "next";
import { DM_Sans, Playfair_Display } from "next/font/google";
import "./globals.css";
import { RestaurantProvider } from "@/hooks/use-restaurant";
import { BottomNav } from "@/components/layout/bottom-nav";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: ["700", "800"],
});

export const metadata: Metadata = {
  title: "YoursTruly Intelligence",
  description: "Your AI-powered business partner for YoursTruly Café",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "YoursTruly",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#7B1A1A",
  viewportFit: "cover", // Enables safe-area-inset-* on iPhones
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${dmSans.variable} ${playfair.variable} font-sans antialiased`}
      >
        <RestaurantProvider>
          <div className="flex min-h-screen flex-col bg-yt-cream">
            {/* Main content — scrollable, padded for bottom nav */}
            <main className="flex-1 overflow-y-auto pb-20">
              {children}
            </main>
            {/* Fixed bottom navigation */}
            <BottomNav />
          </div>
        </RestaurantProvider>
      </body>
    </html>
  );
}
