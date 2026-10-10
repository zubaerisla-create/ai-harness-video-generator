"use client";

import React, { useEffect } from "react";
import { Film, Download, X } from "lucide-react";

interface VideoModalProps {
  video: {
    id: string;
    title: string;
    url?: string;
  } | null;
  onClose: () => void;
}

export default function VideoModal({ video, onClose }: VideoModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!video) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4">
      <div className="bg-white border-8 border-black shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] max-w-xl w-full p-6 relative animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex justify-between items-center pb-4 mb-4 border-b-4 border-black gap-4">
          <h3 className="font-display font-black text-xl uppercase truncate text-black">
            {video.title}
          </h3>
          <button
            onClick={onClose}
            className="w-10 h-10 border-4 border-black bg-black text-white hover:bg-lms-primary flex items-center justify-center font-black transition-colors shrink-0"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* 9:16 Vertical Video Frame */}
        <div className="aspect-[9/16] max-h-[62vh] mx-auto bg-black border-4 border-black overflow-hidden flex items-center justify-center relative shadow-brutalist">
          {video.url ? (
            <video
              src={video.url}
              controls
              autoPlay
              playsInline
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="text-white text-center p-8">
              <Film className="w-16 h-16 mx-auto mb-4 text-lms-primary animate-pulse" />
              <div className="font-display font-black text-xl uppercase">
                Demonstration Short Reel
              </div>
              <p className="text-xs text-gray-400 mt-2">
                720x1280 9:16 Vertical Format
              </p>
            </div>
          )}
        </div>

        {/* Footer info & buttons */}
        <div className="mt-6 flex flex-wrap justify-between items-center border-t-4 border-black pt-4 gap-3">
          <span className="font-bold text-xs uppercase text-gray-700">
            AI Story Video Engine • 720p HD
          </span>
          <div className="flex items-center gap-3">
            {video.url && (
              <a
                href={video.url}
                download
                className="btn-outline px-4 py-2 text-xs flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                DOWNLOAD
              </a>
            )}
            <button
              onClick={onClose}
              className="btn-black px-6 py-2 text-xs"
            >
              CLOSE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
