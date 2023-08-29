from concurrent.futures import ThreadPoolExecutor

max_workers = 10  # Number of threads in the thread pool

thread_pool = ThreadPoolExecutor(max_workers=max_workers)
