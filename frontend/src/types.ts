export interface ItineraryItem {
  day: number;
  title: string;
  description: string;
}

export interface PackageDetail {
  name: string;
  slug: string;
  source_url: string;
  country?: string | null;
  region?: string | null;
  destination?: string | null;
  destinations: string[];
  duration?: string | null;
  nights?: number | null;
  days?: number | null;
  tour_type?: string | null;
  group_size?: number | string | null;
  languages: string[];
  price?: number | null;
  currency?: string | null;
  overview?: string | null;
  itinerary: ItineraryItem[];
  included: string[];
  excluded: string[];
  banner_image?: string | null;
  banner_image_local?: string | null;
  images: string[];
  images_local?: (string | null)[];
  image_download_status?: 'pending' | 'completed' | 'partial' | 'failed' | 'skipped';
  image_download_summary?: {
    total: number;
    downloaded: number;
    failed: number;
    skipped: number;
  } | null;
  location?: string | null;
  source: string;
  scraped_at: string;
}

export interface ScrapeError {
  url: string;
  error: string;
}

export interface ScrapeResult {
  source: string;
  listing_url: string;
  page_title?: string | null;
  country?: string | null;
  region?: string | null;
  destination?: string | null;
  total_packages: number;
  success_count: number;
  failed_count: number;
  scraped_at: string;
  packages: PackageDetail[];
  errors: ScrapeError[];
  image_download_status?: string | null;
  image_download_summary?: {
    total: number;
    downloaded: number;
    failed: number;
    skipped: number;
  } | null;
}

export interface JobStatus {
  job_id: string;
  status:
    | 'queued'
    | 'analyzing'
    | 'discovering'
    | 'scraping'
    | 'downloading_images'
    | 'exporting'
    | 'transforming'
    | 'completed'
    | 'completed_with_errors'
    | 'failed';
  stage: string;
  total: number;
  completed: number;
  success: number;
  failed: number;
  progress_percent: number;
  current_package?: string | null;
  output_file?: string | null;
  django_output_file?: string | null;
  market?: 'india' | 'international' | null;
  django_schema?: string | null;
  image_download_status?: 'pending' | 'in_progress' | 'completed' | 'partial' | 'failed' | 'skipped' | null;
  image_download_summary?: {
    total: number;
    downloaded: number;
    failed: number;
    skipped: number;
  } | null;
  error_message?: string | null;
}

