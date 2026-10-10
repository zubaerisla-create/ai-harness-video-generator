"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Film,
  Play,
  Download,
  Plus,
  RefreshCw,
  FolderOpen
} from "lucide-react";
import VideoModal from "../../components/VideoModal";

interface VideoItem {
  id: string;
  job_id: string;
  title: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
  file_size: number;
  created_at: string;
  download_url: string;
  thumbnail_url?: string;
}

export default function VaultPage() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeVideo, setActiveVideo] = useState<{ id: string; title: string; url?: string } | null>(null);

  const fetchVideos = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/videos?limit=50");
      if (res.ok) {
        const data = await res.json();
        setVideos(data);
      }
    } catch {
      // optimistic fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
    const interval = setInterval(fetchVideos, 6000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-12 sm:py-16 px-4 sm:px-6 lg:px-12 xl:px-20 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
        <div>
          <div className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 font-black uppercase tracking-widest text-xs mb-3 border-2 border-black shadow-brutalist-red">
            ⚡ ARCHIVE & EXPORTS
          </div>
          <h1 className="text-4xl sm:text-6xl font-black font-display uppercase tracking-tighter text-black">
            VIDEO <span className="text-lms-primary">VAULT</span>
          </h1>
          <p className="text-gray-700 font-bold uppercase tracking-wider text-sm mt-2">
            Fully synthesized, render-complete 720p 9:16 vertical short stories ready for Facebook Reels & YouTube Shorts.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0 self-start sm:self-auto">
          <button
            onClick={fetchVideos}
            className="btn-outline px-4 py-2.5 text-xs flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            REFRESH
          </button>
          <Link
            href="/studio"
            className="btn-primary px-6 py-2.5 text-xs flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            NEW STORY
          </Link>
        </div>
      </div>

      {/* Videos Grid */}
      {videos.length === 0 ? (
        <div className="bg-white border-4 border-black p-16 text-center shadow-brutalist-xl">
          <Film className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="font-display font-black text-2xl uppercase mb-2 text-black">
            No Videos in Vault Yet
          </h3>
          <p className="text-gray-600 text-sm max-w-md mx-auto mb-6 font-bold">
            Generate your first short video in the Story Studio or let the 24/7 Auto-Pilot render the daily batch.
          </p>
          <Link
            href="/studio"
            className="btn-primary px-8 py-3 text-sm inline-block"
          >
            OPEN STORY STUDIO
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {videos.map((vid) => (
            <div
              key={vid.id}
              className="card-brutalist overflow-hidden flex flex-col justify-between bg-white"
            >
              <div className="aspect-[9/16] bg-black relative flex items-center justify-center overflow-hidden border-b-4 border-black group">
                {vid.thumbnail_url ? (
                  <img
                    src={vid.thumbnail_url}
                    alt={vid.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-neutral-900 via-neutral-800 to-black flex flex-col items-center justify-center text-white font-black text-lg p-4 text-center">
                    <Film className="w-10 h-10 mb-2 text-lms-primary" />
                    <span className="text-xs uppercase line-clamp-3">{vid.title}</span>
                  </div>
                )}

                {/* Hover Play Button */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <button
                    onClick={() =>
                      setActiveVideo({
                        id: vid.id,
                        title: vid.title,
                        url: vid.download_url,
                      })
                    }
                    className="w-14 h-14 bg-lms-primary border-4 border-black text-white flex items-center justify-center shadow-brutalist transform hover:scale-110 transition-transform"
                    aria-label="Play video"
                  >
                    <Play className="w-7 h-7 fill-white ml-0.5" />
                  </button>
                </div>

                {/* Duration Badge */}
                <div className="absolute bottom-2 right-2 bg-black text-white text-[10px] font-black px-2 py-0.5 border border-white">
                  {vid.duration ? `${vid.duration.toFixed(0)}s` : "45s"}
                </div>
              </div>

              {/* Card Details */}
              <div className="p-4 space-y-3">
                <div>
                  <h4 className="font-display font-black text-base uppercase truncate text-black" title={vid.title}>
                    {vid.title}
                  </h4>
                  <p className="text-[11px] font-bold text-gray-600 mt-0.5">
                    {vid.width || 720}x{vid.height || 1280} • {(vid.file_size / (1024 * 1024)).toFixed(1)} MB • {vid.fps || 24} FPS
                  </p>
                </div>

                <div className="flex gap-2 pt-2 border-t-2 border-black">
                  <button
                    onClick={() =>
                      setActiveVideo({
                        id: vid.id,
                        title: vid.title,
                        url: vid.download_url,
                      })
                    }
                    className="btn-outline flex-1 py-1.5 text-xs text-center flex items-center justify-center gap-1.5"
                  >
                    <Play className="w-3.5 h-3.5 fill-black" />
                    PREVIEW
                  </button>
                  <a
                    href={vid.download_url}
                    download
                    className="btn-black flex-1 py-1.5 text-xs text-center flex items-center justify-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" />
                    DOWNLOAD
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Video Preview Modal */}
      <VideoModal video={activeVideo} onClose={() => setActiveVideo(null)} />
    </section>
  );
}
