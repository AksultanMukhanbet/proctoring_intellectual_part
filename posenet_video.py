import webcam_demo
import glob
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str, default='')
args = parser.parse_args()

start_time = time.time()
list_of_files = glob.glob(args.path + "*.*")
for i in list_of_files:
    print(i)
    webcam_demo.main(i)

print('Time: ', time.time() - start_time)