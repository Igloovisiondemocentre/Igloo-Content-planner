from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from igloo_experience_builder.builder.ui_server import serve_builder_ui
from igloo_experience_builder.capability.classifier import CapabilityClassifier
from igloo_experience_builder.capability.decision_log import DecisionLogger
from igloo_experience_builder.capability.evaluation import BatchEvaluationRunner, DEFAULT_EVAL_FILES
from igloo_experience_builder.capability.reporting import ReportGenerator
from igloo_experience_builder.config import Settings
from igloo_experience_builder.ingestion.common import fetch_text
from igloo_experience_builder.ingestion.pdf_docs import PdfReader
from igloo_experience_builder.ingestion.source_manager import SourceManager
from igloo_experience_builder.local.install_discovery import LocalInstallDiscovery
from igloo_experience_builder.logging_utils import configure_logging
from igloo_experience_builder.sandbox.discovery import SandboxDiscoveryService
from igloo_experience_builder.sandbox.live_state import SandboxLiveStateService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="igloo-experience-builder", description="Igloo Experience Builder Pilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health-check", help="Run source and sandbox health checks.")
    subparsers.add_parser("discover-api", help="Summarize runtime API discovery and safe sandbox probes.")

    ask_parser = subparsers.add_parser("ask", help="Answer a feasibility question.")
    ask_parser.add_argument("question", nargs="+", help="Question to assess.")

    builder_parser = subparsers.add_parser("builder-ui", help="Launch the local Phase 2 mixed-media session builder.")
    builder_parser.add_argument("--host", default="127.0.0.1", help="Host to bind the local builder UI server to.")
    builder_parser.add_argument("--port", type=int, default=8765, help="Port to bind the local builder UI server to.")
    builder_parser.add_argument("--no-browser", action="store_true", help="Start the server without opening a browser window.")

    evaluate_parser = subparsers.add_parser("evaluate", help="Batch-run saved pilot briefs.")
    evaluate_parser.add_argument(
        "files",
        nargs="*",
        help="Evaluation JSON files. Defaults to tests/evals/core_eval_seed.json and tests/evals/hero_eval.json.",
    )

    report_parser = subparsers.add_parser("report", help="Read a saved report.")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)
    report_subparsers.add_parser("last", help="Print the most recent report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = Settings.from_env(Path.cwd())
    configure_logging(settings.log_level)

    if args.command == "health-check":
        return handle_health_check(settings)
    if args.command == "discover-api":
        return handle_discover_api(settings)
    if args.command == "ask":
        return handle_ask(settings, " ".join(args.question).strip())
    if args.command == "builder-ui":
        return handle_builder_ui(settings, host=args.host, port=args.port, open_browser=not args.no_browser)
    if args.command == "evaluate":
        return handle_evaluate(settings, [Path(item) for item in args.files] if args.files else list(DEFAULT_EVAL_FILES))
    if args.command == "report" and args.report_command == "last":
        return handle_report_last(settings)
    parser.print_help()
    return 1


def handle_health_check(settings: Settings) -> int:
    manager = SourceManager(settings)
    sandbox = SandboxDiscoveryService(settings).run()
    live_state = SandboxLiveStateService(settings).snapshot()
    local_install = LocalInstallDiscovery(settings).discover()
    output: dict[str, object] = {
        "project": "Igloo Experience Builder Pilot",
        "phase": "Experience Feasibility Copilot",
        "index_exists": settings.index_path.exists(),
        "manifest_exists": settings.manifest_path.exists(),
        "pdf_ingestion_available": PdfReader is not None,
        "pdfs_found": len(list(settings.cwd.glob("*.pdf"))),
        "runtime_api_source": probe_url(settings.runtime_api_root_url, settings.request_timeout_seconds),
        "platform_docs_source": probe_url(settings.platform_docs_root_url, settings.request_timeout_seconds),
        "sandbox_configured": settings.sandbox_is_configured,
        "sandbox_target": {
            "host": settings.sandbox_host,
            "port": settings.sandbox_port,
            "transport": settings.sandbox_transport,
        },
        "sandbox_validation": {
            "state": sandbox.validation_status.state,
            "summary": sandbox.validation_status.summary,
            "details": sandbox.validation_status.details,
            "surfaces": sandbox.surfaces,
        },
        "sandbox_live_state": {
            "state": live_state.state,
            "summary": live_state.summary,
            "details": live_state.details,
            "event_names": live_state.event_names,
            "source_snapshot": live_state.source_snapshot,
        },
        "local_install": local_install,
        "index_summary": None,
    }
    if settings.index_path.exists():
        index = manager.store.load()
        if index is not None:
            output["index_summary"] = {
                "built_at": index.built_at,
                "source_count": len(index.sources),
                "fragment_count": len(index.fragments),
                "warnings": index.warnings,
            }
    print(json.dumps(output, indent=2))
    return 0


def handle_discover_api(settings: Settings) -> int:
    manager = SourceManager(settings)
    index = manager.ensure_index(refresh=False)
    runtime_sources = [source for source in index.sources if source.source_type.value == "runtime_api"]
    sandbox = SandboxDiscoveryService(settings).run()
    live_state = SandboxLiveStateService(settings).snapshot()
    local_install = LocalInstallDiscovery(settings).discover()
    output = {
        "runtime_api_root": settings.runtime_api_root_url,
        "runtime_api_sources": [
            {"title": source.title, "location": source.canonical_location, "freshness": source.freshness_status.value}
            for source in runtime_sources
        ],
        "local_sandbox": {
            "configured": settings.sandbox_is_configured,
            "host": settings.sandbox_host,
            "port": settings.sandbox_port,
            "transport": settings.sandbox_transport,
            "state": sandbox.validation_status.state,
            "summary": sandbox.validation_status.summary,
            "details": sandbox.validation_status.details,
            "surfaces": sandbox.surfaces,
            "disclaimer": sandbox.validation_status.disclaimer,
        },
        "sandbox_live_state": {
            "state": live_state.state,
            "summary": live_state.summary,
            "details": live_state.details,
            "event_names": live_state.event_names,
            "source_snapshot": live_state.source_snapshot,
            "selected_snapshot": live_state.selected_snapshot,
        },
        "local_install": local_install,
    }
    print(json.dumps(output, indent=2))
    return 0


def handle_ask(settings: Settings, question: str) -> int:
    manager = SourceManager(settings)
    index = manager.ensure_index(refresh=False)
    classifier = CapabilityClassifier(index=index, sandbox=SandboxDiscoveryService(settings))
    assessment = classifier.assess(question)
    report = ReportGenerator().to_markdown(assessment)
    logger = DecisionLogger(settings.reports_dir, settings.decisions_dir)
    logger.persist(assessment, report)
    safe_print(report)
    return 0


def handle_report_last(settings: Settings) -> int:
    report_path = settings.reports_dir / "last_report.md"
    if not report_path.exists():
        print("No report has been generated yet.")
        return 1
    safe_print(report_path.read_text(encoding="utf-8"))
    return 0


def handle_builder_ui(settings: Settings, host: str, port: int, open_browser: bool) -> int:
    serve_builder_ui(settings, host=host, port=port, open_browser=open_browser)
    return 0


def handle_evaluate(settings: Settings, files: list[Path]) -> int:
    resolved_files = [(settings.cwd / path).resolve() if not path.is_absolute() else path for path in files]
    missing_files = [str(path) for path in resolved_files if not path.exists()]
    if missing_files:
        print(json.dumps({"status": "error", "missing_files": missing_files}, indent=2))
        return 1
    manager = SourceManager(settings)
    index = manager.ensure_index(refresh=False)
    sandbox = SandboxDiscoveryService(settings)
    classifier = CapabilityClassifier(index=index, sandbox=sandbox)
    runner = BatchEvaluationRunner(classifier=classifier, evaluations_dir=settings.evaluations_dir)
    payload = runner.evaluate_files(resolved_files)
    print(json.dumps(payload, indent=2))
    return 0


def probe_url(url: str, timeout_seconds: int) -> dict[str, str]:
    try:
        document = fetch_text(url, timeout_seconds)
        return {"status": "ok", "url": url, "length": str(len(document.text))}
    except Exception as exc:
        return {"status": "error", "url": url, "error": str(exc)}


def safe_print(text: str) -> None:
    output = f"{text}\n"
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.buffer.write(output.encode(encoding, errors="replace"))


if __name__ == "__main__":
    raise SystemExit(main())
