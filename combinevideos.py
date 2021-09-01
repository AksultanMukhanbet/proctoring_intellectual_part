import glob
import argparse
import time

from itertools import groupby

from moviepy.editor import VideoFileClip, concatenate_videoclips

parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str, default='')
args = parser.parse_args()

list_of_files = glob.glob(args.path + "*.*")


groups = []

for key, group in groupby(list_of_files, lambda x: x.split('\\')[-1][:12]):
    raw = []
    for thing in group:
        raw.append(thing)
    
    if len(raw) > 1:
        videofileclipraw = []
        for i in raw:
            videofileclipraw.append(VideoFileClip(i))
        final_video = concatenate_videoclips(videofileclipraw)
        final_video.write_videofile(raw[0][:-18] + '.mp4')
