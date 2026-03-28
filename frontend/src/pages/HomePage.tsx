import { useCallback, useEffect, useMemo, useState } from "react";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormatSelector } from "../components/FormatSelector";
import { Header } from "../components/Header";
import { HeroSection } from "../components/HeroSection";
import { JobProgressSection } from "../components/JobProgressSection";
import { formatChoiceSummary, StartJobCard } from "../components/StartJobCard";
import { SuccessSection } from "../components/SuccessSection";
import { VideoMetadataCard } from "../components/VideoMetadataCard";
import { useCreateJob } from "../hooks/useCreateJob";
import { useJobPolling } from "../hooks/useJobPolling";
import { useMetadataFetch } from "../hooks/useMetadataFetch";
import type { JobStatusResponse, MetadataResponse } from "../types";
import { looksLikeHttpUrl } from "../utils/validators";

const LS_JOB = "convert_site_active_job";

function pickAdvancedOutputType(formats: MetadataResponse["formats"], formatId: string): "video" | "audio" {
  const row = formats.find((f) => f.format_id === formatId);
  if (!row) return "video";
  const v = row.vcodec;
  if (!v || v === "none") return "audio";
  return "video";
}

export function HomePage() {
  const [url, setUrl] = useState("");
  const [urlClientError, setUrlClientError] = useState<string | null>(null);
  const [meta, setMeta] = useState<MetadataResponse | null>(null);
  const [simpleKey, setSimpleKey] = useState("best");
  const [advanced, setAdvanced] = useState(false);
  const [advancedFormatId, setAdvancedFormatId] = useState("");
  const [jobId, setJobId] = useState<string | null>(() => localStorage.getItem(LS_JOB));
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [pollFatal, setPollFatal] = useState<string | null>(null);

  const { fetchMetadata, loading: metaLoading, error: metaHookError, setError: setMetaHookError } =
    useMetadataFetch();
  const { create: createJob, loading: jobCreating, error: jobHookError, setError: setJobHookError } =
    useCreateJob();

  const choices = meta?.normalized_choices ?? [];
  const selectedChoice = useMemo(
    () => choices.find((c) => c.key === simpleKey),
    [choices, simpleKey]
  );

  useEffect(() => {
    if (meta?.recommended_choice_key) {
      setSimpleKey(meta.recommended_choice_key);
    }
  }, [meta?.recommended_choice_key]);

  useEffect(() => {
    if (meta?.formats?.length && !advancedFormatId) {
      setAdvancedFormatId(meta.formats[0].format_id);
    }
  }, [meta, advancedFormatId]);

  const onJobUpdate = useCallback((s: JobStatusResponse) => {
    setJob(s);
    setPollFatal(null);
    if (["completed", "failed", "expired"].includes(s.status)) {
      localStorage.removeItem(LS_JOB);
    }
  }, []);

  const onPollFatal = useCallback((msg: string) => {
    setPollFatal(msg);
  }, []);

  useJobPolling(jobId, onJobUpdate, onPollFatal);

  const handleUrlChange = (v: string) => {
    setUrl(v);
    setUrlClientError(null);
    setMetaHookError(null);
    setJobHookError(null);
  };

  const handleAnalyze = async () => {
    setMetaHookError(null);
    setJobHookError(null);
    setPollFatal(null);
    if (!looksLikeHttpUrl(url)) {
      setUrlClientError("Please enter a valid http(s) URL.");
      return;
    }
    setJobId(null);
    setJob(null);
    localStorage.removeItem(LS_JOB);
    const data = await fetchMetadata(url.trim());
    if (data) {
      setMeta(data);
    }
  };

  const startSummary = useMemo(() => {
    if (advanced) {
      const row = meta?.formats.find((f) => f.format_id === advancedFormatId);
      const label = row
        ? [row.format_id, row.resolution || (row.height ? `${row.height}p` : ""), row.ext]
            .filter(Boolean)
            .join(" · ")
        : advancedFormatId;
      return formatChoiceSummary(undefined, label);
    }
    return formatChoiceSummary(selectedChoice, "");
  }, [advanced, advancedFormatId, meta?.formats, selectedChoice]);

  const handleStartJob = async () => {
    if (!meta || !looksLikeHttpUrl(url)) return;
    setJobHookError(null);
    setPollFatal(null);

    let format_id: string;
    let output_type: "video" | "audio";
    let preset_key: string | null = null;

    if (advanced) {
      if (!advancedFormatId) {
        setJobHookError("Pick a format from the list.");
        return;
      }
      format_id = advancedFormatId;
      output_type = pickAdvancedOutputType(meta.formats, advancedFormatId);
      preset_key = null;
    } else {
      const c = choices.find((x) => x.key === simpleKey);
      if (!c) {
        setJobHookError("Select a format.");
        return;
      }
      format_id = c.format_id;
      output_type = c.output_type === "audio" ? "audio" : "video";
      preset_key = simpleKey;
    }

    const res = await createJob({
      url: url.trim(),
      format_id,
      output_type,
      preset_key,
    });
    if (res) {
      setJobId(res.job_id);
      localStorage.setItem(LS_JOB, res.job_id);
      setJob({
        job_id: res.job_id,
        status: res.status,
        progress: 0,
        status_label: "Queued",
      });
    }
  };

  const resetAll = () => {
    setUrl("");
    setMeta(null);
    setJobId(null);
    setJob(null);
    setAdvanced(false);
    setAdvancedFormatId("");
    setSimpleKey("best");
    setUrlClientError(null);
    setMetaHookError(null);
    setJobHookError(null);
    setPollFatal(null);
    localStorage.removeItem(LS_JOB);
  };

  const combinedError = metaHookError || jobHookError || pollFatal;
  const showMeta = !!meta;
  const jobTerminal = job && ["completed", "failed", "expired"].includes(job.status);

  return (
    <div className="min-h-screen flex flex-col pb-16">
      <Header />
      <main className="flex-1 max-w-xl mx-auto w-full px-4 py-8 sm:py-12 space-y-8">
        <HeroSection
          url={url}
          onUrlChange={handleUrlChange}
          onSubmit={handleAnalyze}
          loading={metaLoading}
          clientError={urlClientError}
        />

        <ErrorBanner
          message={combinedError}
          onDismiss={() => {
            setMetaHookError(null);
            setJobHookError(null);
            setPollFatal(null);
          }}
        />

        {showMeta && (
          <>
            <VideoMetadataCard meta={meta!} />
            <FormatSelector
              choices={choices}
              selectedKey={simpleKey}
              onSelectKey={setSimpleKey}
              advanced={advanced}
              onToggleAdvanced={setAdvanced}
              formats={meta!.formats}
              advancedFormatId={advancedFormatId}
              onAdvancedFormatId={setAdvancedFormatId}
            />
            <StartJobCard
              summary={startSummary}
              loading={jobCreating}
              disabled={!meta || metaLoading}
              onStart={handleStartJob}
            />
          </>
        )}

        {jobId &&
          (!job || !["completed", "failed", "expired"].includes(job.status)) && (
            <JobProgressSection job={job} />
          )}

        {job?.status === "completed" && <SuccessSection job={job} onNewDownload={resetAll} />}

        {job?.status === "failed" && (
          <ErrorBanner
            title="Download failed"
            message={job.error || "Please try another format or try again later."}
            onDismiss={() => setJob(null)}
          />
        )}

        {job?.status === "expired" && (
          <ErrorBanner
            title="File expired"
            message="This download is no longer available. Start a new job with the same link."
            onDismiss={resetAll}
          />
        )}

        {showMeta && (
          <button
            type="button"
            onClick={resetAll}
            className="text-sm text-slate-500 hover:text-slate-300 underline underline-offset-2"
          >
            Start over
          </button>
        )}
      </main>
    </div>
  );
}
