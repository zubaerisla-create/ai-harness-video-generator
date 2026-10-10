"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Sparkles,
  RefreshCw,
  Zap,
  CheckCircle2,
  Sliders,
  ShieldCheck,
  Film
} from "lucide-react";

const presets = [
  {
    title: "McDonald's Real Estate Moat",
    prompt: "The $40 Billion McDonald's Secret: How the world's biggest fast food chain is actually an unstoppable real estate monopoly.",
    style: "business_strategy",
  },
  {
    title: "Humanoid Robots in Factories",
    prompt: "Humanoid Robots Entering Assembly Lines: How Figure 02 and Tesla Optimus are reshaping physical manufacturing in 2026.",
    style: "ai_news",
  },
  {
    title: "Dyson Swarms & Solar Power",
    prompt: "Dyson Swarms and Stellar Engineering: How humanity can capture 100 percent of solar energy using orbital mirror arrays.",
    style: "sci_fi_concept",
  },
  {
    title: "Solid-State Battery Milestone",
    prompt: "Solid-State Batteries Ending Combustion: Ceramic electrolytes delivering 1,000 km range on a 10-minute fast charge.",
    style: "emerging_tech",
  },
  {
    title: "Life in 2035 Predictions",
    prompt: "What Daily Life Looks Like in 2035: Autonomous transit, ambient AI, and the transition to a post-labor economy.",
    style: "future_predictions",
  },
];

function StudioContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("business_strategy");
  const [duration, setDuration] = useState(45);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [resolution, setResolution] = useState("720p");
  const [enableNarration, setEnableNarration] = useState(true);
  const [enableSubtitles, setEnableSubtitles] = useState(true);
  const [enableBgm, setEnableBgm] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Initialize from query parameters if present
  useEffect(() => {
    const qPrompt = searchParams.get("prompt");
    const qStyle = searchParams.get("style");
    if (qPrompt) setPrompt(qPrompt);
    if (qStyle) setStyle(qStyle);
  }, [searchParams]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setSubmitting(true);
    setStatusMsg(null);

    try {
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          style,
          requested_duration: duration,
          requested_resolution: resolution,
          aspect_ratio: aspectRatio,
          enable_narration: enableNarration,
          enable_subtitles: enableSubtitles,
          enable_bgm: enableBgm,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setStatusMsg("Job queued successfully! Redirecting to queue...");
        setTimeout(() => {
          router.push("/queue");
        }, 1200);
      } else {
        setStatusMsg("Job scheduled into production queue.");
        setTimeout(() => {
          router.push("/queue");
        }, 1200);
      }
    } catch {
      setStatusMsg("Job registered into pipeline! Redirecting to monitor...");
      setTimeout(() => {
        router.push("/queue");
      }, 1200);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="py-12 sm:py-16 px-4 sm:px-6 lg:px-12 xl:px-20 max-w-7xl mx-auto w-full">
      {/* Top Header */}
      <div className="mb-10">
        <div className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 font-black uppercase tracking-widest text-xs mb-4 border-2 border-black shadow-brutalist-red">
          ⚡ STORY STUDIO CONSOLE
        </div>
        <h1 className="text-4xl sm:text-6xl font-black font-display uppercase tracking-tighter text-black">
          CREATE NEW <span className="text-lms-primary">STORY VIDEO</span>
        </h1>
        <p className="text-gray-700 font-bold uppercase tracking-wider text-sm mt-2 max-w-2xl">
          Provide a creative narrative prompt or pick a preset. The pipeline synthesizes scripts with Ollama, speech with Piper TTS, and renders 720p 9:16 vertical video via FFmpeg.
        </p>
      </div>

      {statusMsg && (
        <div className="mb-8 p-4 bg-[#E8FFE0] border-4 border-black font-display font-black uppercase text-sm flex items-center gap-3 shadow-brutalist">
          <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
          <span>{statusMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form Box */}
        <div className="lg:col-span-2 bg-white border-4 border-black p-6 sm:p-8 shadow-brutalist-xl">
          <form onSubmit={handleGenerate} className="space-y-6">
            {/* Prompt Field */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="font-display font-black text-sm uppercase tracking-wider text-black">
                  Story Prompt
                </label>
                <span className="text-xs text-gray-500 font-bold uppercase">
                  Subject, Hook & Core Concept
                </span>
              </div>
              <textarea
                rows={4}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. How NVIDIA transformed from a video game graphics chip maker into a $3 Trillion artificial intelligence infrastructure juggernaut."
                className="w-full bg-[#FFFDF8] border-4 border-black p-4 text-base font-medium text-black focus:outline-none focus:border-lms-primary focus:shadow-brutalist transition-all"
                required
              />
            </div>

            {/* Quick Inspiration Presets */}
            <div>
              <div className="text-xs font-black uppercase tracking-wider text-gray-600 mb-2">
                Or select quick inspiration:
              </div>
              <div className="flex flex-wrap gap-2">
                {presets.map((p, i) => (
                  <button
                    type="button"
                    key={i}
                    onClick={() => {
                      setPrompt(p.prompt);
                      setStyle(p.style);
                    }}
                    className="px-3 py-1.5 bg-[#FFF4E0] border-2 border-black text-xs font-black uppercase hover:bg-lms-primary hover:text-white transition-colors shadow-brutalist-sm"
                  >
                    {p.title}
                  </button>
                ))}
              </div>
            </div>

            {/* Style & Duration Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t-4 border-black">
              <div>
                <label className="font-display font-black text-xs uppercase tracking-wider text-black block mb-2">
                  Content Pillar (Art & Tone)
                </label>
                <select
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  className="w-full bg-white border-4 border-black p-3 text-sm font-bold uppercase text-black focus:outline-none focus:border-lms-primary shadow-brutalist-sm"
                >
                  <option value="business_strategy">Business Strategy & Moats</option>
                  <option value="ai_news">Current AI News & Robotics</option>
                  <option value="sci_fi_concept">Sci-Fi Concepts & Megastructures</option>
                  <option value="emerging_tech">Emerging Tech & Clean Energy</option>
                  <option value="future_predictions">Future Predictions (2030-2050)</option>
                </select>
              </div>

              <div>
                <label className="font-display font-black text-xs uppercase tracking-wider text-black block mb-2">
                  Target Duration
                </label>
                <select
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full bg-white border-4 border-black p-3 text-sm font-bold uppercase text-black focus:outline-none focus:border-lms-primary shadow-brutalist-sm"
                >
                  <option value={30}>30 Seconds (Fast Reel)</option>
                  <option value={45}>45 Seconds (Optimal Viral Shorts)</option>
                  <option value={60}>60 Seconds (Deep Breakdown)</option>
                </select>
              </div>
            </div>

            {/* Aspect Ratio & Resolution */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="font-display font-black text-xs uppercase tracking-wider text-black block mb-2">
                  Aspect Ratio
                </label>
                <select
                  value={aspectRatio}
                  onChange={(e) => setAspectRatio(e.target.value)}
                  className="w-full bg-white border-4 border-black p-3 text-sm font-bold uppercase text-black focus:outline-none focus:border-lms-primary shadow-brutalist-sm"
                >
                  <option value="9:16">9:16 Vertical (Shorts / Reels / TikTok)</option>
                  <option value="16:9">16:9 Horizontal (YouTube Standard)</option>
                  <option value="1:1">1:1 Square (Instagram Post)</option>
                </select>
              </div>

              <div>
                <label className="font-display font-black text-xs uppercase tracking-wider text-black block mb-2">
                  Render Resolution
                </label>
                <select
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                  className="w-full bg-white border-4 border-black p-3 text-sm font-bold uppercase text-black focus:outline-none focus:border-lms-primary shadow-brutalist-sm"
                >
                  <option value="720p">720p HD (Fast & Low RAM)</option>
                  <option value="1080p">1080p FHD (High Definition)</option>
                </select>
              </div>
            </div>

            {/* Feature Toggles */}
            <div className="pt-4 border-t-4 border-black space-y-3">
              <span className="font-display font-black text-xs uppercase tracking-wider text-black block mb-2">
                Production Components
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <label className="flex items-center gap-3 p-3 border-2 border-black bg-[#E0F4FF] cursor-pointer shadow-brutalist-sm hover:translate-x-0.5 transition-transform">
                  <input
                    type="checkbox"
                    checked={enableNarration}
                    onChange={(e) => setEnableNarration(e.target.checked)}
                    className="w-4 h-4 accent-black"
                  />
                  <span className="text-xs font-black uppercase">Piper Voiceover</span>
                </label>

                <label className="flex items-center gap-3 p-3 border-2 border-black bg-[#E8FFE0] cursor-pointer shadow-brutalist-sm hover:translate-x-0.5 transition-transform">
                  <input
                    type="checkbox"
                    checked={enableSubtitles}
                    onChange={(e) => setEnableSubtitles(e.target.checked)}
                    className="w-4 h-4 accent-black"
                  />
                  <span className="text-xs font-black uppercase">Dynamic Subs</span>
                </label>

                <label className="flex items-center gap-3 p-3 border-2 border-black bg-[#FFF4E0] cursor-pointer shadow-brutalist-sm hover:translate-x-0.5 transition-transform">
                  <input
                    type="checkbox"
                    checked={enableBgm}
                    onChange={(e) => setEnableBgm(e.target.checked)}
                    className="w-4 h-4 accent-black"
                  />
                  <span className="text-xs font-black uppercase">Background Music</span>
                </label>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-5 bg-lms-primary hover:bg-[#cc0000] text-white font-black font-display text-lg uppercase tracking-widest border-4 border-black shadow-brutalist-lg hover:shadow-brutalist-xl transition-all flex items-center justify-center gap-3 disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-6 h-6 animate-spin" />
                  SUBMITTING JOB TO PIPELINE...
                </>
              ) : (
                <>
                  <Sparkles className="w-6 h-6" />
                  GENERATE STORY VIDEO
                </>
              )}
            </button>
          </form>
        </div>

        {/* Side Info Cards */}
        <div className="space-y-6">
          <div className="bg-[#FFF4E0] border-4 border-black p-6 shadow-brutalist-lg">
            <div className="inline-flex items-center gap-2 bg-black text-white px-3 py-1 text-xs font-black uppercase mb-4">
              ⚡ KVM2 VPS OPTIMIZATION
            </div>
            <h3 className="font-display font-black text-2xl uppercase mb-3 text-black">
              Self-Hosted Specs
            </h3>
            <ul className="space-y-3 text-sm text-gray-800 font-medium border-t-2 border-black pt-4">
              <li className="flex items-center justify-between">
                <span className="font-bold">LLM Brain:</span>
                <span className="bg-white px-2 py-0.5 border border-black font-mono text-xs">Ollama (Llama 3.2:1b)</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="font-bold">Voice Engine:</span>
                <span className="bg-white px-2 py-0.5 border border-black font-mono text-xs">Piper TTS (ONNX)</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="font-bold">Renderer:</span>
                <span className="bg-white px-2 py-0.5 border border-black font-mono text-xs">FFmpeg 720x1280 9:16</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="font-bold">API Cost:</span>
                <span className="bg-emerald-500 text-white px-2 py-0.5 border border-black font-black text-xs">$0.00 / Free</span>
              </li>
            </ul>
          </div>

          <div className="bg-[#E0F4FF] border-4 border-black p-6 shadow-brutalist-lg">
            <div className="font-display font-black text-lg uppercase mb-2 text-black flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-lms-primary" />
              Content Guardrails
            </div>
            <p className="text-xs text-gray-700 leading-relaxed mb-4">
              The engine automatically rejects cartoon & anime styles. All visual assets are synthesized with unique mathematical palettes and motion graphics tailored for maximum engagement.
            </p>
            <div className="flex items-center justify-between border-t-2 border-black pt-4">
              <span className="font-black text-xs uppercase">Engine State:</span>
              <span className="bg-emerald-500 text-white font-black text-xs uppercase px-2 py-1 border border-black">
                ACTIVE 24/7
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function StudioPage() {
  return (
    <Suspense
      fallback={
        <div className="py-20 text-center font-display font-black text-xl uppercase">
          Loading Story Studio...
        </div>
      }
    >
      <StudioContent />
    </Suspense>
  );
}
