class RetryableScanError(Exception):
    """Transient failure (network, GitHub 429/5xx).

    Raised by the scan pipeline so the arq worker can retry the job with
    exponential backoff instead of marking it failed immediately.
    """
