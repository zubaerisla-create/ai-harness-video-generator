"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Play,
  Film,
  Sparkles,
  Zap,
  CheckCircle2,
  Clock,
  ArrowRight,
  Flame,
  Star,
  Check,
  Video,
  Layers,
  ChevronRight,
  Volume2,
  Subtitles,
  Music,
  Server,
  Activity,
  Award
} from "lucide-react";
import VideoModal from "../components/VideoModal";

export default function Home() {
  const [activeVideo, setActiveVideo] = useState<{ id: string; title: string; url?: string } | null>(null);

  // 5 Content Pillars Presets (No anime or cartoons)
  const presets = [
    {
      title: "McDonald's Real Estate Moat",
      prompt: "The $40 Billion McDonald's Secret: How the world's biggest fast food chain is actually an unstoppable real estate monopoly.",
      style: "business_strategy",
      tag: "BUSINESS STRATEGY",
      color: "bg-[#FFF4E0]",
    },
    {
      title: "Humanoid Robots in Factories",
      prompt: "Humanoid Robots Entering Assembly Lines: How Figure 02 and Tesla Optimus are reshaping physical manufacturing in 2026.",
      style: "ai_news",
      tag: "AI NEWS",
      color: "bg-[#E0F4FF]",
    },
    {
      title: "Dyson Swarms & Solar Power",
      prompt: "Dyson Swarms and Stellar Engineering: How humanity can capture 100 percent of solar energy using orbital mirror arrays.",
      style: "sci_fi_concept",
      tag: "SCI-FI REALITY",
      color: "bg-[#F0E0FF]",
    },
    {
      title: "Solid-State Battery Milestone",
      prompt: "Solid-State Batteries Ending Combustion: Ceramic electrolytes delivering 1,000 km range on a 10-minute fast charge.",
      style: "emerging_tech",
      tag: "EMERGING TECH",
      color: "bg-[#E8FFE0]",
    },
    {
      title: "Life in 2035 Predictions",
      prompt: "What Daily Life Looks Like in 2035: Autonomous transit, ambient AI, and the transition to a post-labor economy.",
      style: "future_predictions",
      tag: "FUTURE PREDICTIONS",
      color: "bg-[#FFF0F5]",
    },
  ];

  // Demo showcase shorts (5 Pillars)
  const demoShorts = [
    {
      id: "demo-1",
      title: "The $40 Billion McDonald's Real Estate Secret",
      duration: "00:45",
      price: "Free",
      tag: "BUSINESS MOAT",
      bgBadge: "bg-[#FFF4E0]",
      thumbText: "BUSINESS STRATEGY",
      gradient: "from-amber-600 via-yellow-600 to-slate-900",
    },
    {
      id: "demo-2",
      title: "Humanoid Robots Are Now Working in Factories",
      duration: "00:45",
      price: "Free",
      tag: "AI BREAKTHROUGH",
      bgBadge: "bg-[#E0F4FF]",
      thumbText: "AI NEWS",
      gradient: "from-blue-600 via-cyan-600 to-slate-900",
    },
    {
      id: "demo-3",
      title: "Dyson Swarms: Capturing 100% of Solar Energy",
      duration: "00:45",
      price: "Free",
      tag: "DEEP PHYSICS",
      bgBadge: "bg-[#F0E0FF]",
      thumbText: "SCI-FI REALITY",
      gradient: "from-purple-700 via-indigo-700 to-black",
    },
    {
      id: "demo-4",
      title: "Solid-State Batteries Just Changed Everything",
      duration: "00:45",
      price: "Free",
      tag: "EMERGING TECH",
      bgBadge: "bg-[#E8FFE0]",
      thumbText: "CLEAN ENERGY",
      gradient: "from-emerald-600 via-teal-700 to-black",
    },
  ];

  return (
    <div className="w-full">
      {/* 1. HERO SECTION (Split polygon red background Neo-Brutalist) */}
      <section className="relative border-b-8 border-black overflow-hidden pt-10 lg:pt-0 bg-white">
        <div className="hidden lg:block absolute top-0 bottom-0 right-0 w-[55%] bg-lms-primary [clip-path:polygon(15%_0,100%_0,100%_100%,0_100%)] z-0"></div>

        <div className="flex flex-col lg:flex-row min-h-[85vh]">
          {/* Hero Left Content */}
          <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-12 xl:px-20 py-12 lg:py-16 relative z-10 bg-transparent">
            {/* Decorative Dot Grid */}
            <div className="absolute right-10 top-20 hidden lg:block opacity-40">
              <svg width="60" height="60" viewBox="0 0 60 60" fill="none">
                {[0, 16, 32, 48].map((x) =>
                  [0, 16, 32, 48].map((y) => (
                    <circle key={`${x}-${y}`} cx={x + 4} cy={y + 4} r="2" fill="#E60000" />
                  ))
                )}
              </svg>
            </div>

            <div className="relative max-w-2xl mx-auto lg:mx-0">
              {/* Top Badge */}
              <div className="inline-flex items-center gap-2 bg-[#1a1a1a] text-white px-4 py-2 text-xs sm:text-sm font-bold uppercase tracking-wider mb-8 rounded-lg border-b-4 border-lms-primary transform -rotate-1">
                🔥 AI STORY VIDEO HARNESS • SELF-HOSTED VPS
              </div>

              {/* Giant Headline */}
              <h1 className="text-6xl sm:text-7xl xl:text-[7.2rem] font-black font-display text-black tracking-tighter leading-[0.9] mb-8 uppercase relative">
                <svg
                  className="absolute -left-8 -top-6 w-10 h-10 text-lms-primary hidden md:block"
                  viewBox="0 0 100 100"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M50 15 L50 35 M25 50 L45 50 M75 25 L60 40 M25 25 L40 40" />
                </svg>
                GENERATE<br />
                <span className="text-stroke-3 hover:text-lms-primary transition-colors cursor-default">
                  VIRAL
                </span><br />
                <span className="relative inline-block">
                  SHORT STORIES
                  <span className="absolute -bottom-2 left-0 w-full h-4 bg-lms-primary/20 -z-10 -rotate-1"></span>
                </span>
              </h1>

              {/* Description */}
              <p className="text-lg sm:text-xl font-bold font-sans text-black mb-10 max-w-xl leading-relaxed border-l-8 border-black pl-4">
                Automated 720p 9:16 vertical short-form video generation system designed for YouTube Shorts and Facebook Reels. Produces 5 genuinely unique videos daily across business strategy, AI news, and sci-fi concepts without cartoons or asset repetition.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-5 mb-12">
                <Link
                  href="/studio"
                  className="btn-primary text-base sm:text-lg px-8 py-4 inline-flex items-center justify-center gap-3 group"
                >
                  <span>START CREATING</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>

                <Link
                  href="/vault"
                  className="btn-outline text-base sm:text-lg px-8 py-4 inline-flex items-center justify-center gap-3"
                >
                  <span>BROWSE VAULT</span>
                  <Film className="w-5 h-5" />
                </Link>
              </div>

              {/* Real-time Hardware Indicator */}
              <div className="flex flex-wrap items-center gap-4 text-xs font-black uppercase text-black pt-6 border-t-4 border-black">
                <div className="flex items-center gap-2 bg-[#FFF4E0] border-2 border-black px-3 py-1.5 shadow-brutalist-sm">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Hostinger KVM2 Active
                </div>
                <div className="flex items-center gap-2 bg-[#E0F4FF] border-2 border-black px-3 py-1.5 shadow-brutalist-sm">
                  <Activity className="w-3.5 h-3.5 text-blue-600" />
                  Ollama Llama 3.2:1b Ready
                </div>
                <div className="flex items-center gap-2 bg-[#E8FFE0] border-2 border-black px-3 py-1.5 shadow-brutalist-sm">
                  <Zap className="w-3.5 h-3.5 text-emerald-600" />
                  Piper TTS Neural Voice
                </div>
              </div>
            </div>
          </div>

          {/* Hero Right Visuals */}
          <div className="flex-1 relative flex items-center justify-center p-8 sm:p-12 lg:p-16 z-10">
            {/* Massive Hero Brutalist Card */}
            <div className="w-full max-w-md bg-white border-8 border-black p-6 shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] relative transform rotate-1 hover:rotate-0 transition-transform duration-300">
              {/* Badge on Card */}
              <div className="absolute -top-6 -right-6 bg-yellow-300 text-black font-display font-black text-sm uppercase px-4 py-2 border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] rotate-6">
                5 VIDEOS / DAY
              </div>

              {/* 9:16 Vertical Reel Simulation Frame */}
              <div className="aspect-[9/16] bg-black border-4 border-black relative overflow-hidden flex flex-col justify-between p-4 text-white">
                <div className="absolute inset-0 bg-gradient-to-b from-black/80 via-transparent to-black/90 pointer-events-none"></div>

                {/* Top reel bar */}
                <div className="relative z-10 flex justify-between items-center text-xs font-mono font-bold">
                  <span className="bg-lms-primary px-2 py-0.5 border border-white">720x1280 9:16</span>
                  <span className="text-gray-300">AI HARNESS REEL</span>
                </div>

                {/* Center Content Preview */}
                <div className="relative z-10 text-center space-y-3 py-12">
                  <div className="w-16 h-16 mx-auto bg-lms-primary border-4 border-white flex items-center justify-center shadow-brutalist animate-bounce">
                    <Play className="w-8 h-8 fill-white ml-1" />
                  </div>
                  <h3 className="font-display font-black text-2xl uppercase tracking-tight text-white drop-shadow-md">
                    THE $40B MCDONALD'S REAL ESTATE SECRET
                  </h3>
                  <div className="inline-block bg-yellow-400 text-black font-black text-xs uppercase px-3 py-1 border-2 border-black">
                    BUSINESS STRATEGY
                  </div>
                </div>

                {/* Bottom Subtitle Karaoke Box */}
                <div className="relative z-10 bg-black/80 border-2 border-white/60 p-3 text-center">
                  <div className="text-xs uppercase text-gray-300 font-bold mb-1">Live Synchronized Subs</div>
                  <p className="text-sm font-black text-yellow-300 leading-snug">
                    "THEY DON'T SELL BURGERS... THEY OWN THE LAND BENEATH THEM."
                  </p>
                </div>
              </div>

              {/* Card Meta Row */}
              <div className="mt-4 flex justify-between items-center text-xs font-bold uppercase text-black pt-3 border-t-4 border-black">
                <span>⚡ FFmpeg 720p Canvas</span>
                <span className="text-lms-primary">No Cartoons • 100% Unique</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. STATS STRIP (Brutalist blocks) */}
      <section className="border-b-8 border-black bg-white">
        <div className="grid grid-cols-2 md:grid-cols-4 divide-y-4 md:divide-y-0 md:divide-x-4 divide-black">
          <div className="p-8 text-center bg-[#FFFDF8]">
            <div className="text-4xl sm:text-6xl font-display font-black text-black">5/DAY</div>
            <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-gray-700 mt-2">
              Autonomous Videos
            </div>
          </div>
          <div className="p-8 text-center bg-[#FFFDF8]">
            <div className="text-4xl sm:text-6xl font-display font-black text-lms-primary">~45s</div>
            <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-gray-700 mt-2">
              Fast Render Speed
            </div>
          </div>
          <div className="p-8 text-center bg-[#FFFDF8]">
            <div className="text-4xl sm:text-6xl font-display font-black text-black">9:16</div>
            <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-gray-700 mt-2">
              Reels & Shorts Canvas
            </div>
          </div>
          <div className="p-8 text-center bg-[#FFFDF8]">
            <div className="text-4xl sm:text-6xl font-display font-black text-emerald-600">$0.00</div>
            <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-gray-700 mt-2">
              Self-Hosted VPS Cost
            </div>
          </div>
        </div>
      </section>

      {/* 3. 5 PILLARS PRESETS SECTION */}
      <section className="py-20 px-4 sm:px-6 lg:px-12 xl:px-20 border-b-8 border-black bg-[#FFFDF8]">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
            <div>
              <div className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 font-black uppercase tracking-widest text-xs mb-3 border-2 border-black shadow-brutalist-red">
                ⚡ 5 CORE CONTENT PILLARS
              </div>
              <h2 className="text-4xl sm:text-6xl font-black font-display uppercase tracking-tight text-black">
                NO CARTOONS. <span className="text-lms-primary">REAL STORIES.</span>
              </h2>
              <p className="text-gray-700 font-bold uppercase tracking-wider text-sm mt-2 max-w-xl">
                Every video is generated with a unique topic, script, scene pacing, and motion graphics. Pick a preset or craft your own in Studio.
              </p>
            </div>

            <Link
              href="/studio"
              className="btn-primary px-6 py-3 text-xs inline-flex items-center gap-2 self-start md:self-auto"
            >
              <span>OPEN STORY STUDIO</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {presets.map((preset, idx) => (
              <div
                key={idx}
                className={`card-brutalist p-6 flex flex-col justify-between ${preset.color}`}
              >
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <span className="tag-badge bg-black text-white text-[10px]">
                      {preset.tag}
                    </span>
                    <span className="font-mono font-black text-xs text-gray-700">0{idx + 1}</span>
                  </div>

                  <h3 className="font-display font-black text-xl uppercase mb-3 text-black">
                    {preset.title}
                  </h3>

                  <p className="text-xs font-medium text-gray-800 leading-relaxed mb-6">
                    "{preset.prompt}"
                  </p>
                </div>

                <Link
                  href={`/studio?prompt=${encodeURIComponent(preset.prompt)}&style=${preset.style}`}
                  className="btn-black py-2.5 px-4 text-xs flex items-center justify-between group"
                >
                  <span>GENERATE THIS STORY</span>
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. PIPELINE CRASH COURSE / ARCHITECTURE */}
      <section className="py-20 px-4 sm:px-6 lg:px-12 xl:px-20 border-b-8 border-black bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <div className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 font-black uppercase tracking-widest text-xs mb-4 border-2 border-black shadow-brutalist-red">
              ⚡ COMPLETE PIPELINE STACK
            </div>
            <h2 className="text-4xl sm:text-6xl font-black font-display uppercase tracking-tight text-black">
              HOW THE <span className="text-lms-primary">ENGINE WORKS</span>
            </h2>
            <p className="text-gray-700 font-bold uppercase tracking-wider text-sm mt-3">
              100% automated, lightweight and self-hosted on Hostinger KVM2 without third-party API costs.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="border-4 border-black p-6 bg-[#FFF4E0] shadow-brutalist">
              <div className="w-12 h-12 bg-black text-white flex items-center justify-center font-display font-black text-xl mb-4 border-2 border-black">
                01
              </div>
              <h3 className="font-display font-black text-lg uppercase mb-2 text-black">
                Ollama Llama 3.2
              </h3>
              <p className="text-xs text-gray-700 font-medium leading-relaxed">
                Generates high-retention viral scripts tailored to the selected pillar. Structured into punchy narration and second-by-second scenes.
              </p>
            </div>

            <div className="border-4 border-black p-6 bg-[#E0F4FF] shadow-brutalist">
              <div className="w-12 h-12 bg-black text-white flex items-center justify-center font-display font-black text-xl mb-4 border-2 border-black">
                02
              </div>
              <h3 className="font-display font-black text-lg uppercase mb-2 text-black">
                Piper Neural TTS
              </h3>
              <p className="text-xs text-gray-700 font-medium leading-relaxed">
                Synthesizes hyper-crisp ONNX voiceovers with natural cadence, zero token fees, and native support for multiple languages.
              </p>
            </div>

            <div className="border-4 border-black p-6 bg-[#E8FFE0] shadow-brutalist">
              <div className="w-12 h-12 bg-black text-white flex items-center justify-center font-display font-black text-xl mb-4 border-2 border-black">
                03
              </div>
              <h3 className="font-display font-black text-lg uppercase mb-2 text-black">
                FFmpeg 720p Canvas
              </h3>
              <p className="text-xs text-gray-700 font-medium leading-relaxed">
                Assembles dynamic camera pans, cinematic color grading, synchronized audio tracks, and burned-in subtitles into clean 9:16 vertical MP4s.
              </p>
            </div>

            <div className="border-4 border-black p-6 bg-[#FFF0F5] shadow-brutalist">
              <div className="w-12 h-12 bg-black text-white flex items-center justify-center font-display font-black text-xl mb-4 border-2 border-black">
                04
              </div>
              <h3 className="font-display font-black text-lg uppercase mb-2 text-black">
                24/7 Auto-Pilot
              </h3>
              <p className="text-xs text-gray-700 font-medium leading-relaxed">
                Background daemon automatically spins up 5 diverse videos every single day. Instant download via web vault for YouTube & Reels posting.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. DEMO SHORTS SHOWCASE */}
      <section className="py-20 px-4 sm:px-6 lg:px-12 xl:px-20 border-b-8 border-black bg-[#FFFDF8]">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
            <div>
              <div className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 font-black uppercase tracking-widest text-xs mb-3 border-2 border-black shadow-brutalist-red">
                ⚡ REELS & SHORTS READY
              </div>
              <h2 className="text-4xl sm:text-6xl font-black font-display uppercase tracking-tight text-black">
                BITE-SIZED <span className="text-lms-primary">SHORTS</span>
              </h2>
              <p className="text-gray-700 font-bold uppercase tracking-wider text-sm mt-2 max-w-xl">
                Clean, distraction-free video output without unwanted "Act 1" labels or header text overlays.
              </p>
            </div>

            <Link
              href="/vault"
              className="btn-outline px-6 py-3 text-xs inline-flex items-center gap-2 self-start md:self-auto"
            >
              <span>EXPLORE ALL ARCHIVES</span>
              <Film className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {demoShorts.map((short) => (
              <div
                key={short.id}
                className="card-brutalist overflow-hidden flex flex-col justify-between bg-white"
              >
                {/* 9:16 Thumbnail */}
                <div className={`aspect-[9/16] bg-gradient-to-br ${short.gradient} relative flex items-center justify-center overflow-hidden border-b-4 border-black group p-4`}>
                  <div className="text-center z-10 text-white space-y-2">
                    <div className="text-[10px] font-black uppercase tracking-widest opacity-80">
                      {short.thumbText}
                    </div>
                    <div className="font-display font-black text-sm uppercase leading-tight line-clamp-3">
                      {short.title}
                    </div>
                  </div>

                  {/* Play Button */}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <button
                      onClick={() =>
                        setActiveVideo({
                          id: short.id,
                          title: short.title,
                        })
                      }
                      className="w-14 h-14 bg-lms-primary border-4 border-black text-white flex items-center justify-center shadow-brutalist transform hover:scale-110 transition-transform"
                    >
                      <Play className="w-7 h-7 fill-white ml-0.5" />
                    </button>
                  </div>

                  <div className="absolute bottom-2 right-2 bg-black text-white text-[10px] font-black px-2 py-0.5 border border-white">
                    {short.duration}
                  </div>
                </div>

                {/* Info */}
                <div className="p-4 space-y-3">
                  <div>
                    <span className="tag-badge bg-[#FFF4E0] text-black text-[10px] mb-2 inline-block">
                      {short.tag}
                    </span>
                    <h4 className="font-display font-black text-sm uppercase text-black line-clamp-2">
                      {short.title}
                    </h4>
                  </div>

                  <div className="pt-2 border-t-2 border-black flex justify-between items-center">
                    <button
                      onClick={() =>
                        setActiveVideo({
                          id: short.id,
                          title: short.title,
                        })
                      }
                      className="text-xs font-black uppercase text-lms-primary hover:underline flex items-center gap-1"
                    >
                      <span>PREVIEW DEMO</span>
                      <Play className="w-3 h-3 fill-lms-primary" />
                    </button>
                    <Link
                      href={`/studio?prompt=${encodeURIComponent(short.title)}`}
                      className="text-xs font-bold uppercase text-black hover:text-lms-primary"
                    >
                      REMIX
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 6. CALL TO ACTION BANNER */}
      <section className="py-20 px-4 sm:px-6 lg:px-12 xl:px-20 bg-lms-primary text-white border-b-8 border-black">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 font-black uppercase tracking-widest text-xs mb-6 border-2 border-white shadow-brutalist-sm">
            ⚡ SCALE YOUR CHANNEL
          </div>
          <h2 className="text-4xl sm:text-6xl font-black font-display uppercase tracking-tight mb-6">
            READY TO RENDER YOUR NEXT VIRAL SHORT?
          </h2>
          <p className="text-lg sm:text-xl font-bold font-sans uppercase mb-8 max-w-2xl mx-auto opacity-95">
            Hop into the Studio, paste your topic, and download your 720p vertical MP4 in less than a minute.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              href="/studio"
              className="px-8 py-4 bg-white text-black font-black font-display text-base uppercase tracking-wider border-4 border-black shadow-brutalist hover:shadow-brutalist-lg transition-all inline-flex items-center justify-center gap-2"
            >
              <span>ENTER STORY STUDIO</span>
              <ArrowRight className="w-5 h-5 text-lms-primary" />
            </Link>
            <Link
              href="/queue"
              className="px-8 py-4 bg-black text-white font-black font-display text-base uppercase tracking-wider border-4 border-white shadow-brutalist hover:shadow-brutalist-lg transition-all inline-flex items-center justify-center gap-2"
            >
              <span>VIEW PIPELINE QUEUE</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Modal for Demo Previews */}
      <VideoModal video={activeVideo} onClose={() => setActiveVideo(null)} />
    </div>
  );
}
