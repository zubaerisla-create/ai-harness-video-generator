"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Film, Layers, X } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [pendingJobs, setPendingJobs] = useState(0);

  useEffect(() => {
    const fetchPending = async () => {
      try {
        const res = await fetch("/api/system/stats");
        if (res.ok) {
          const d = await res.json();
          setPendingJobs(d.pending_jobs || 0);
        }
      } catch {
        // Ignore fallback
      }
    };
    fetchPending();
    const interval = setInterval(fetchPending, 10000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { name: "HOME", href: "/" },
    { name: "STUDIO", href: "/studio" },
    { name: "JOB QUEUE", href: "/queue", badge: pendingJobs > 0 },
    { name: "VIDEO VAULT", href: "/vault" },
    { name: "TELEMETRY", href: "/telemetry" },
  ];

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <nav id="site-nav" className="sticky top-0 z-50 bg-white border-b-4 border-black transition-shadow duration-200">
      <div className="w-full px-4 sm:px-6 lg:px-12 xl:px-20 mx-auto">
        <div className="flex items-center justify-between h-20">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-3 font-display font-black text-2xl tracking-tighter hover:text-lms-primary transition-colors"
          >
            <div className="w-10 h-10 bg-black text-white flex items-center justify-center border-2 border-black shadow-brutalist-sm hover:bg-lms-primary transition-colors">
              <Film className="w-5 h-5 text-white" />
            </div>
            <span className="text-black uppercase">AI HARNESS</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative font-display font-black text-sm uppercase tracking-widest px-4 py-2 transition-colors flex items-center gap-1.5 ${
                    active
                      ? "text-lms-primary underline decoration-4 underline-offset-8"
                      : "text-black hover:text-lms-primary"
                  }`}
                >
                  {link.name}
                  {link.badge && (
                    <span className="w-2 h-2 rounded-full bg-lms-primary animate-ping"></span>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Auth / Action */}
          <div className="flex items-center gap-4">
            <div className="hidden lg:flex items-center gap-2 bg-[#FFF4E0] border-2 border-black px-3 py-1 shadow-brutalist-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-display font-black text-[11px] uppercase tracking-wider text-black">
                Hostinger KVM2 Active
              </span>
            </div>

            <Link
              href="/studio"
              className="btn-primary px-6 py-2.5 text-xs inline-flex items-center justify-center"
            >
              START CREATING
            </Link>

            {/* Hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 border-2 border-black hover:bg-black hover:text-white transition-colors"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Layers className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Nav Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden pb-6 border-t-4 border-black pt-4">
            <div className="flex flex-col gap-2">
              {navLinks.map((link) => {
                const active = isActive(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`px-4 py-3 font-display font-black text-sm uppercase tracking-widest text-left border-2 border-black flex items-center justify-between ${
                      active ? "bg-lms-primary text-white" : "hover:bg-[#FFF4E0] text-black"
                    }`}
                  >
                    <span>{link.name}</span>
                    {link.badge && (
                      <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
