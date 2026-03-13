"""
Batch file testing tool for the file-parser backend.

Usage:
    python test_batch.py [OPTIONS]

Options:
    --dir PATH        Directory containing files to test (default: ./test_files)
    --url URL         Backend URL (default: http://localhost:8000/upload)
    --output PATH     Output CSV/JSON path (default: ./test_results_<timestamp>)
    --format FORMAT   Output format: csv or json (default: csv)
    --workers N       Number of concurrent workers (default: 1)
    --timeout N       Request timeout in seconds (default: 300)

Examples:
    python test_batch.py --dir ./samples
    python test_batch.py --dir ./samples --workers 3 --format json
    python test_batch.py --dir ./samples --url http://localhost:8000/upload --output ./results
"""

import argparse
import asyncio
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import httpx
from PIL import Image


class FileResult(TypedDict):
    filename: str
    file_size_kb: float
    resolution: str
    response_time_s: float | None
    http_status: int | None
    companyName: str | None
    entityIdentifier: str | None
    countryISOCode: str | None
    companyType: str | None
    error: str | None

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}

CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def get_file_size_kb(path: Path) -> float:
    """Return file size in KB, rounded to 2 decimal places."""
    return round(path.stat().st_size / 1024, 2)


def get_image_resolution(path: Path) -> str:
    """Return WxH for images, or 'N/A' for non-image files (e.g. PDF)."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "N/A"
    try:
        with Image.open(path) as img:
            w, h = img.size
            return f"{w}x{h}"
    except Exception:
        return "ERROR"


async def send_file(
    client: httpx.AsyncClient,
    path: Path,
    url: str,
    timeout: float,
) -> FileResult:
    """Upload a single file and return a result record."""
    ext = path.suffix.lower()
    content_type = CONTENT_TYPE_MAP.get(ext, "application/octet-stream")
    file_size_kb = get_file_size_kb(path)
    resolution = get_image_resolution(path)

    result: FileResult = {
        "filename": path.name,
        "file_size_kb": file_size_kb,
        "resolution": resolution,
        "response_time_s": None,
        "http_status": None,
        "companyName": None,
        "entityIdentifier": None,
        "countryISOCode": None,
        "companyType": None,
        "error": None,
    }

    try:
        with open(path, "rb") as f:
            file_bytes = f.read()

        start = time.perf_counter()
        response = await client.post(
            url,
            files={"file": (path.name, file_bytes, content_type)},
            timeout=timeout,
        )
        elapsed_s = round(time.perf_counter() - start, 2)

        result["response_time_s"] = elapsed_s
        result["http_status"] = response.status_code

        if response.status_code == 200:
            data = response.json()
            result["companyName"] = data.get("companyName")
            result["entityIdentifier"] = data.get("entityIdentifier")
            result["countryISOCode"] = data.get("countryISOCode")
            result["companyType"] = data.get("companyType")
        else:
            result["error"] = response.text[:300]

    except httpx.TimeoutException:
        result["error"] = f"Timeout after {timeout}s"
    except Exception as exc:
        result["error"] = str(exc)[:300]

    return result


def collect_files(directory: Path) -> list[Path]:
    """Collect all supported files from a directory (non-recursive)."""
    files = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return files


def save_csv(results: list[FileResult], output_path: Path) -> None:
    if not results:
        return
    fieldnames = list(results[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def save_json(results: list[FileResult], output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def print_summary(results: list[FileResult], total_elapsed: float) -> None:
    total = len(results)
    success = sum(1 for r in results if r["http_status"] == 200)
    failed = total - success
    times: list[float] = [r["response_time_s"] for r in results if r["response_time_s"] is not None]
    avg_time = round(sum(times) / len(times), 2) if times else 0.0
    max_time = round(max(times), 2) if times else 0.0
    min_time = round(min(times), 2) if times else 0.0

    print("\n" + "=" * 60)
    print("📊  Test Summary")
    print("=" * 60)
    print(f"  Total files     : {total}")
    print(f"  ✅ Success       : {success}")
    print(f"  ❌ Failed        : {failed}")
    print(f"  Avg response    : {avg_time} s")
    print(f"  Min response    : {min_time} s")
    print(f"  Max response    : {max_time} s")
    print(f"  Total wall time : {round(total_elapsed, 2)} s")
    print("=" * 60)


async def run_batch(
    files: list[Path],
    url: str,
    timeout: float,
    workers: int,
) -> list[FileResult]:
    """Process files with a semaphore-limited concurrency pool."""
    semaphore = asyncio.Semaphore(workers)
    results: list[FileResult | None] = [None] * len(files)
    batch_start = time.perf_counter()

    async with httpx.AsyncClient() as client:

        async def bounded_send(index: int, path: Path) -> None:
            async with semaphore:
                print(f"🔍 Testing: {path.name}")
                result = await send_file(client, path, url, timeout)
                results[index] = result

                elapsed = round(time.perf_counter() - batch_start, 1)
                status_icon = "✅" if result["http_status"] == 200 else "❌"
                print(
                    f"[{elapsed:>7.1f}s] {status_icon} {result['filename']}"
                    f"  |  {result['file_size_kb']} KB"
                    f"  |  {result['resolution']}"
                    f"  |  {result['response_time_s']} s"
                    f"  |  HTTP {result['http_status']}"
                )
                if result["error"]:
                    print(f"           ⚠️  Error: {result['error']}")
                else:
                    print(
                        f"           company={result['companyName']}"
                        f"  id={result['entityIdentifier']}"
                        f"  country={result['countryISOCode']}"
                        f"  type={result['companyType']}"
                    )

        await asyncio.gather(*(bounded_send(i, f) for i, f in enumerate(files)))

    return [r for r in results if r is not None]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch test the file-parser backend with a folder of files."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("./tests/test_files"),
        help="Directory containing files to test (default: ./tests/test_files)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000/upload",
        help="Backend upload URL (default: http://localhost:8000/upload)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path without extension (default: ./test_results_<timestamp>)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format: csv or json (default: csv)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent requests (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Per-request timeout in seconds (default: 300)",
    )
    args = parser.parse_args()

    # Validate input directory
    if not args.dir.exists() or not args.dir.is_dir():
        print(f"❌  Directory not found: {args.dir}")
        print(f"    Create it and place your test files inside, e.g.:")
        print(f"      mkdir -p {args.dir}")
        raise SystemExit(1)

    files = collect_files(args.dir)
    if not files:
        print(f"❌  No supported files found in {args.dir}")
        print(f"    Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        raise SystemExit(1)

    # Determine output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = args.output or Path(f"./test_results_{timestamp}")
    output_path = output_base.with_suffix(f".{args.format}")

    print("=" * 60)
    print(f"🚀  File Parser — Batch Test")
    print("=" * 60)
    print(f"  Target URL  : {args.url}")
    print(f"  Test folder : {args.dir.resolve()}")
    print(f"  Files found : {len(files)}")
    print(f"  Workers     : {args.workers}")
    print(f"  Timeout     : {args.timeout}s")
    print(f"  Output      : {output_path.resolve()}")
    print("=" * 60 + "\n")

    wall_start = time.perf_counter()
    results = asyncio.run(run_batch(files, args.url, args.timeout, args.workers))
    wall_elapsed = time.perf_counter() - wall_start

    # Save results
    if args.format == "csv":
        save_csv(results, output_path)
    else:
        save_json(results, output_path)

    print_summary(results, wall_elapsed)
    print(f"\n💾  Results saved to: {output_path.resolve()}\n")


if __name__ == "__main__":
    main()
