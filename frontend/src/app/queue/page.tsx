"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  RefreshCw,
  Film,
  Play,
  Plus,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Layers
} from "lucide-react";
import VideoModal from "../../components/VideoModal";

interface Job {
  id: string;
  prompt: string;
  style: string;
  status: string;
  stage?: string;
  progress: number;
  requested_duration: number;
  created_at?: string;
  video?: {
    id: string;
    title: string;
  };
}

export default function QueuePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeVideo, setActiveVideo] = useState<{ id: string; title: string; url?: string } | null>(null);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/jobs?limit=50");
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch {
      // optimistic fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, []);

  const completedCount = jobs.filter((j) => j.status === "completed").length;
  const processingCount = jobs.filter((j) => j.status === "processing").length;
  const pendingCount = jobs.filter((j) => j.status === "pending").length;
  const failedCount = jobs.filter((j) => j.status === "failed").length;

  return (
    <section className="py-12 sm:py-16 px-4 sm:px-6 lg:px-12 xl:px-20 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
        <div>
          <div className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 font-black uppercase tracking-widest text-xs mb-3 border-2 border-black shadow-brutalist-red">
            ⚡ REAL-TIME PIPELINE MONITOR
          </div>
          <h1 className="text-4xl sm:text-6xl font-black font-display uppercase tracking-tighter text-black">
            ACTIVE JOB <span className="text-lms-primary">QUEUE</span>
          </h1>
          <p className="text-gray-700 font-bold uppercase tracking-wider text-sm mt-2">
            Live execution status of ongoing script synthesis, audio voicing, and FFmpeg video assemblies.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0 self-start sm:self-auto">
          <button
            onClick={fetchJobs}
            className="btn-outline px-4 py-2.5 text-xs flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            REFRESH
          </button>
          <Link
            href="/studio"
            className="btn-primary px-5 py-2.5 text-xs flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            NEW JOB
          </Link>
        </div>
      </div>

      {/* Summary Stat Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <div className="bg-[#FFF4E0] border-4 border-black p-4 shadow-brutalist-sm">
          <div className="text-[11px] font-black uppercase tracking-wider text-gray-700">Total In Queue</div>
          <div className="text-3xl font-display font-black text-black mt-1">{jobs.length}</div>
        </div>
        <div className="bg-[#E0F4FF] border-4 border-black p-4 shadow-brutalist-sm">
          <div className="text-[11px] font-black uppercase tracking-wider text-blue-800">Processing</div>
          <div className="text-3xl font-display font-black text-lms-primary mt-1">{processingCount}</div>
        </div>
        <div className="bg-[#E8FFE0] border-4 border-black p-4 shadow-brutalist-sm">
          <div className="text-[11px] font-black uppercase tracking-wider text-emerald-800">Completed</div>
          <div className="text-3xl font-display font-black text-emerald-600 mt-1">{completedCount}</div>
        </div>
        <div className="bg-[#FFF0F0] border-4 border-black p-4 shadow-brutalist-sm">
          <div className="text-[11px] font-black uppercase tracking-wider text-rose-800">Pending / Other</div>
          <div className="text-3xl font-display font-black text-black mt-1">{pendingCount + failedCount}</div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border-4 border-black shadow-brutalist-xl overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b-4 border-black bg-[#FFF4E0]">
              <th className="p-4 font-display font-black text-xs uppercase tracking-wider">Job ID</th>
              <th className="p-4 font-display font-black text-xs uppercase tracking-wider">Story Prompt</th>
              <th className="p-4 font-display font-black text-xs uppercase tracking-wider">Pillar</th>
              <th className="p-4 font-display font-black text-xs uppercase tracking-wider">Status</th>
              <th className="p-4 font-display font-black text-xs uppercase tracking-wider">Progress</th>
              <th className="p-4 font-display font-black text-xs uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y-2 divide-black">
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-16 text-center text-gray-600 font-bold uppercase text-sm">
                  <Film className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  No jobs currently queued.
                  <div className="mt-4">
                    <Link href="/studio" className="btn-primary px-6 py-2 text-xs inline-block">
                      Create a Video in Studio
                    </Link>
                  </div>
                </td>
              </tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id} className="hover:bg-[#FFFDF8] transition-colors">
                  <td className="p-4 font-mono font-bold text-xs">{job.id.substring(0, 8)}</td>
                  <td className="p-4 font-bold text-sm max-w-xs truncate" title={job.prompt}>
                    {job.prompt}
                  </td>
                  <td className="p-4">
                    <span className="tag-badge bg-black text-white text-[10px] whitespace-nowrap">
                      {job.style}
                    </span>
                  </td>
                  <td className="p-4 whitespace-nowrap">
                    <span
                      className={`tag-badge text-[10px] ${
                        job.status === "completed"
                          ? "bg-emerald-500 text-white"
                          : job.status === "processing"
                          ? "bg-lms-primary text-white animate-pulse"
                          : job.status === "failed"
                          ? "bg-rose-600 text-white"
                          : "bg-amber-400 text-black"
                      }`}
                    >
                      {job.status} {job.stage ? `(${job.stage})` : ""}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="w-28 bg-gray-200 border-2 border-black h-3">
                      <div
                        className="bg-lms-primary h-full transition-all"
                        style={{ width: `${job.progress}%` }}
                      ></div>
                    </div>
                  </td>
                  <td className="p-4 text-right space-x-2 whitespace-nowrap">
                    {job.video && (
                      <button
                        onClick={() =>
                          setActiveVideo({
                            id: job.video!.id,
                            title: job.video!.title,
                            url: `/api/videos/${job.video!.id}/download`,
                          })
                        }
                        className="btn-primary px-3 py-1 text-[10px] inline-flex items-center gap-1"
                      >
                        <Play className="w-3 h-3 fill-white" />
                        WATCH
                      </button>
                    )}
                    {job.status === "completed" && !job.video && (
                      <Link
                        href="/vault"
                        className="btn-outline px-3 py-1 text-[10px] inline-flex items-center gap-1"
                      >
                        VIEW IN VAULT
                      </Link>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Video Preview Modal */}
      <VideoModal video={activeVideo} onClose={() => setActiveVideo(null)} />
    </section>
  );
}
