# download.py
import aiohttp
import asyncio
import aiofiles

MAX_RETRIES = 3
CONCURRENT_DOWNLOADS = 64
CHUNK_SIZE = 1 * 1024 * 1024  # 1 MB

async def download_range(session, link, start, end, filename, attempt=1):
    headers = {'Range': f'bytes={start}-{end}'}
    try:
        async with session.get(link, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status in [200, 206]:
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(await response.read())
                print(f"✅ Downloaded: {filename} ({start}-{end})")
                return True
            else:
                raise Exception(f"Unexpected status: {response.status}")
    except Exception as e:
        print(f"⚠ Retry {attempt}/{MAX_RETRIES} failed for {filename}: {e}")
        if attempt < MAX_RETRIES:
            await asyncio.sleep(0.5 * attempt)
            return await download_range(session, link, start, end, filename, attempt + 1)
        else:
            print(f"❌ Failed: {filename} after {MAX_RETRIES} retries")
            return False

async def parallel_downloader(link, chunk_list, shared, progress_callback=None):
    connector = aiohttp.TCPConnector(limit=CONCURRENT_DOWNLOADS)
    async with aiohttp.ClientSession(connector=connector) as session:
        async def wrapped_download(start, end, filename):
            result = await download_range(session, link, start, end, filename)
            shared['done'] += 1
            if progress_callback:
                progress_callback(shared['done'] / shared['total'])
            return result

        tasks = [
            asyncio.create_task(wrapped_download(start, end, filename))
            for start, end, filename in chunk_list
        ]
        results = await asyncio.gather(*tasks)
        failed = [chunk_list[i] for i, success in enumerate(results) if not success]
        if failed:
            print(f"\n🔥 {len(failed)} chunks failed. Rerun script if needed.")
        else:
            print("\n🚀 All chunks downloaded successfully!")

def create_chunks(file_size, chunk_size, extension):
    return [
        [start, min(start + chunk_size - 1, file_size - 1), f"{extension}_part{start // chunk_size}.{extension}"]
        for start in range(0, file_size, chunk_size)
    ]

async def main(video_stream, audio_stream, video_size, audio_size, progress_cb=None):
    video_chunk_list = create_chunks(video_size, CHUNK_SIZE, "mp4")
    audio_chunk_list = create_chunks(audio_size, CHUNK_SIZE, "m4a")
    shared = {'done': 0, 'total': len(video_chunk_list) + len(audio_chunk_list)}

    await asyncio.gather(
        parallel_downloader(video_stream, video_chunk_list, shared, progress_callback=progress_cb),
        parallel_downloader(audio_stream, audio_chunk_list, shared, progress_callback=progress_cb)
    )
