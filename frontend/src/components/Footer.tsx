"use client";

import React from "react";
import Link from "next/link";
import { Film } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t-8 border-black pt-20 pb-10 bg-footer-bg mt-auto">
      <div className="w-full px-4 sm:px-6 lg:px-12 xl:px-20 mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-14 mb-16">
          {/* Column 1 */}
          <div className="md:col-span-2">
            <Link
              href="/"
              className="inline-flex items-center gap-3 font-display font-black text-3xl tracking-tighter mb-8 text-black hover:text-lms-primary transition-colors"
            >
              <div className="w-10 h-10 bg-black text-white flex items-center justify-center border-2 border-black shadow-brutalist-sm">
                <Film className="w-5 h-5 text-white" />
              </div>
              <span className="uppercase">AI STORY HARNESS</span>
            </Link>
            <p className="max-w-md text-lg text-black font-sans font-bold border-l-8 border-lms-primary pl-6 leading-relaxed">
              Empowering content creators worldwide with autonomous AI-led story video generation and multi-channel production. Built for YouTube Shorts & Facebook Reels.
            </p>
          </div>

          {/* Column 2 - Navigation */}
          <div>
            <h4 className="font-display font-black text-black uppercase tracking-widest text-sm mb-6 border-b-4 border-black inline-block pb-1">
              PLATFORM
            </h4>
            <ul className="space-y-3">
              <li>
                <Link
                  href="/studio"
                  className="font-display font-bold text-black hover:text-white hover:bg-black px-3 py-1.5 -ml-3 transition-all inline-block uppercase text-sm border-2 border-transparent hover:border-black"
                >
                  Story Studio
                </Link>
              </li>
              <li>
                <Link
                  href="/queue"
                  className="font-display font-bold text-black hover:text-white hover:bg-black px-3 py-1.5 -ml-3 transition-all inline-block uppercase text-sm border-2 border-transparent hover:border-black"
                >
                  Job Queue
                </Link>
              </li>
              <li>
                <Link
                  href="/vault"
                  className="font-display font-bold text-black hover:text-white hover:bg-black px-3 py-1.5 -ml-3 transition-all inline-block uppercase text-sm border-2 border-transparent hover:border-black"
                >
                  Video Vault
                </Link>
              </li>
              <li>
                <Link
                  href="/telemetry"
                  className="font-display font-bold text-black hover:text-white hover:bg-black px-3 py-1.5 -ml-3 transition-all inline-block uppercase text-sm border-2 border-transparent hover:border-black"
                >
                  System Status
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3 - Specs */}
          <div>
            <h4 className="font-display font-black text-black uppercase tracking-widest text-sm mb-6 border-b-4 border-black inline-block pb-1">
              SPECS & TECH
            </h4>
            <ul className="space-y-3 font-bold text-sm uppercase text-gray-700">
              <li>Ollama Llama 3.2:1b</li>
              <li>Piper TTS (Bangla/English)</li>
              <li>FFmpeg 720p 9:16 Video</li>
              <li>Hostinger KVM2 VPS</li>
            </ul>
          </div>
        </div>

        {/* Social & Copyright */}
        <div className="border-t-4 border-black pt-8 flex flex-col md:flex-row justify-between items-center gap-6">
          <p className="font-display font-black uppercase text-xs tracking-widest text-black">
            &copy; 2026 AI STORY VIDEO HARNESS. ALL RIGHTS RESERVED.
          </p>

          <div className="font-display font-black text-xs uppercase tracking-widest text-white border-4 border-black px-5 py-2.5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] bg-lms-primary">
            BUILT FOR LIFELONG CREATORS
          </div>
        </div>
      </div>
    </footer>
  );
}
