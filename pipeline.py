"""
Run a batch as a pipeline: local preparation one document at a time, network
work (OpenAI) several documents at a time.

    prepare(job)            runs in the calling thread, strictly one after another
                            (CPU/disk work such as cutting PDFs to page ranges)
    process(job, prepared)  runs in a pool of `workers` threads
                            (upload, wait for the model, save the result)
    on_result(job, result, error)
                            runs in the calling thread as each document finishes,
                            so it is safe for console output and Streamlit updates
    cleanup(prepared)       deletes the temporary files of a document that never started
    on_interrupt()          called on Ctrl+C, before waiting for running documents

Preparation stays only a little ahead of the workers (at most `workers` prepared
documents waiting), so uploads start straight away and few temporary files exist
at once. If the run is interrupted (Ctrl+C, or Stop in the web UI), no new
documents are started, documents already being processed finish and are saved,
and the temporary files of documents that never started are deleted.
"""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Callable, Iterable, Optional


def run_pipeline(jobs: Iterable[Any],
                 prepare: Callable[[Any], Any],
                 process: Callable[[Any, Any], Any],
                 on_result: Callable[[Any, Any, Optional[BaseException]], None],
                 workers: int,
                 cleanup: Callable[[Any], None] = lambda prepared: None,
                 on_interrupt: Optional[Callable[[], None]] = None) -> None:
    workers = max(1, int(workers))
    max_in_flight = workers * 2  # running + prepared and waiting for a free worker
    executor = ThreadPoolExecutor(max_workers=workers)
    in_flight = {}  # future -> (job, prepared)

    def report(future) -> None:
        job, _prepared = in_flight.pop(future)
        try:
            on_result(job, future.result(), None)
        except Exception as e:  # raised by process(); reported, never fatal
            on_result(job, None, e)

    def collect(block: bool) -> None:
        if not in_flight:
            return
        done, _ = wait(list(in_flight), timeout=None if block else 0, return_when=FIRST_COMPLETED)
        for future in done:
            report(future)

    try:
        for job in jobs:
            try:
                prepared = prepare(job)
            except Exception as e:
                on_result(job, None, e)
                collect(block=False)
                continue
            in_flight[executor.submit(process, job, prepared)] = (job, prepared)
            # Report anything already finished; wait if enough work is queued
            collect(block=len(in_flight) >= max_in_flight)
        while in_flight:
            collect(block=True)
    except KeyboardInterrupt:
        if on_interrupt:
            on_interrupt()  # e.g. tell the user, before waiting for running documents
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
        # Delete temporary files of documents that never started, before anything
        # that might itself be interrupted (e.g. a Streamlit update after Stop)
        for future in [f for f in in_flight if f.cancelled()]:
            _job, prepared = in_flight.pop(future)
            try:
                cleanup(prepared)
            except Exception:
                pass
        # Report documents that finished while shutting down
        for future in list(in_flight):
            report(future)
