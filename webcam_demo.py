import torch
import cv2
import time
import argparse

import posenet

import requests

import datetime as dt
import mysql.connector as msql
mydb = msql.connect(host="192.168.12.3", user="netuser", passwd='987', database='proctoring')
mycursor = mydb.cursor()


parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str, default=0)
args = parser.parse_args()

def frame_skip(cap, n_skip):
    for _ in range(n_skip):
        cap.grab()

def insert_db(video_path, log_type, video_time):
    barcode, quiz_id = video_path.split("\\")[-1][:7], video_path.split("\\")[-1][7:12]

    currentTime = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "INSERT INTO `video_logs` (`datetime`, `video_name`, `basr_code`, `quiz_id`, `log_type`, `log_time`) VALUES (%s,%s,%s,%s,%s,%s);"
    val = (str(currentTime), str(video_path), int(barcode), int(quiz_id), str(log_type), str(video_time))
    mycursor.execute(sql, val)
    mydb.commit()

def post_request_json_data(video_path, log_type, video_time):
    barcode, quiz_id = video_path.split("\\")[-1][:7], video_path.split("\\")[-1][7:12]

    json_data = {"barcode": int(barcode), "quiz_id": int(quiz_id), "suspicious_type": int(log_type), "video_ref": str(video_path.split("\\")[-1]), "time": int(video_time)}

    r = requests.post('http://192.168.12.16/proctoringadmin/api/Suspicious/insert_video_action', json=json_data)


def main(video_path):
    try:
        __ = (int(video_path.split("\\")[-1][:7]), int(video_path.split("\\")[-1][7:12]))
        model = posenet.load_model(50)
        model = model.cuda()
        output_stride = model.output_stride

        cap = cv2.VideoCapture(video_path)
        cap.set(3, 640)
        cap.set(4, 480)
        
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        video_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        timer = 0
        n_skip = 30
        frame_count = 0
        start = time.time()

        prev_frame_time = 0
        new_frame_time = 0

        no_people = 0
        many_people = 0
        turn_head = 0

        video_time = ''
        video_type = ''
        
        while video_length > timer:
            frame_skip(cap, n_skip)

            input_image, display_image, output_scale = posenet.read_cap(
                cap, scale_factor=0.4, output_stride=output_stride)
            
            with torch.no_grad():
                input_image = torch.Tensor(input_image).cuda()

                heatmaps_result, offsets_result, displacement_fwd_result, displacement_bwd_result = model(input_image)

                pose_scores, keypoint_scores, keypoint_coords = posenet.decode_multiple_poses(
                    heatmaps_result.squeeze(0),
                    offsets_result.squeeze(0),
                    displacement_fwd_result.squeeze(0),
                    displacement_bwd_result.squeeze(0),
                    output_stride=output_stride,
                    max_pose_detections=2,
                    min_pose_score=0.15)

            keypoint_coords *= output_scale

            # TODO this isn't particularly fast, use GL for drawing and display someday...
            overlay_image = posenet.draw_skel_and_kp(
                display_image, pose_scores, keypoint_scores, keypoint_coords,
                min_pose_score=0.15, min_part_score=0.1)

            try:
                if keypoint_scores[:][0:3].mean() == 0 and no_people == 0:
                    second = timer/video_fps
                    if second < 20:
                        pass
                    else:
                        print(round(second//60), ':', round(second%60), 'No people')
                        video_time = str(round(second//3600)) + ':' + str(round(second//60)%60) + ':' + str(round(second%60))

                        no_people = 1
                        post_request_json_data(video_path, 11, second)
                elif keypoint_scores[:][0:3].mean() > 0. and ((keypoint_scores[0][3] > 0.8 and keypoint_scores[0][4] > 0.8) or (keypoint_scores[1][3] > 0.8 and keypoint_scores[1][4] > 0.8)):
                    no_people = 0    
                if keypoint_scores[1].mean() > 0.5 and many_people == 0:
                    second = timer/video_fps
                    if second < 20:
                        pass
                    else:
                        print(round(second//60), ':', round(second%60), 'Many people')
                        video_time = str(round(second//3600)) + ':' + str(round(second//60)%60) + ':' + str(round(second%60))
                        many_people = 1
                        post_request_json_data(video_path, 10, second)
                elif keypoint_scores[1].sum() == 0:
                    many_people = 0 
                if ((keypoint_scores[0][3] < 0.1 or keypoint_scores[0][4] < 0.1) or (keypoint_scores[0][3] < 0.1 or keypoint_scores[0][4] < 0.1)) and turn_head == 0 and no_people == 0:
                    second = timer/video_fps
                    if second < 20:
                        pass
                    else:
                        print(round(second//60), ':', round(second%60), 'Turn Head')
                        video_time = str(round(second//3600)) + ':' + str(round(second//60)%60) + ':' + str(round(second%60))
                        turn_head = 1
                        post_request_json_data(video_path, 9, second)
                elif (keypoint_scores[0][3] > 0.8 and keypoint_scores[0][4] > 0.8):
                    turn_head = 0
            except:
                pass
    

            new_frame_time = time.time()

            if frame_count%30 == 0:
                fps = round(30/(new_frame_time-prev_frame_time), 2)
                prev_frame_time = new_frame_time 
            cv2.putText(overlay_image, 'FPS: ' + str(fps), (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 0), 1, cv2.LINE_AA)

            cv2.imshow('posenet', overlay_image)
            frame_count += 1
            timer += n_skip

            # id, datetime, video_name, video_log_type, video_log_time
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except:
        pass
    try:
        print('Average FPS: ', frame_count / (time.time() - start))
        print('Time: ', time.time() - start)
    except:
        pass
if __name__ == "__main__":
    main(args.path)