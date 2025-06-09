import React from "react";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css";
import { UserProvider } from "@/hooks/useUser";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Grishinium ID - Your Decentralized Identity",
  description: "Create your decentralized identity on the Grishinium blockchain",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-[#0e0024] text-white`}>
        <UserProvider>
          {children}
        </UserProvider>
      </body>
    </html>
  );
}
