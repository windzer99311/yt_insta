import subprocess
import os

from natsort import natsorted  # pip install natsort

def combine_chunks(extension):

    part_files = natsorted([f for f in os.listdir() if f.endswith(f".{extension}") and f.startswith(f"{extension}_part")])
    output_file = f"{extension}.{'mp4' if extension=='mp4' else 'm4a'}"

    with open(f"{extension}_concat.bin", 'wb') as wfd:
        for f in part_files:
            with open(f, 'rb') as fd:
                wfd.write(fd.read())
                print(len(fd.read()))
            print(len(f))
            os.remove(f)
    if os.path.exists(output_file):
        os.remove(output_file)
    os.rename(f"{extension}_concat.bin", output_file)
    print(f"✅ Combined {extension} chunks into {output_file}")
    return output_file

def merge_video_audio(video_file, audio_file, output_file="output.mp4"):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-i", audio_file,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        output_file
        ]
    subprocess.run(cmd)
    os.remove(video_file)
    os.remove(audio_file)
    print(f"🎬 Merged video+audio into {output_file}")
    with open(output_file,'rb') as f:
        video_byte=f.read()
    return "✅ Merging complete!",video_byte