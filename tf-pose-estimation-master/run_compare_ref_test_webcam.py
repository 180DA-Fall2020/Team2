import argparse
import logging
import sys
import time


from tf_pose import common
import cv2
import numpy as np
from tf_pose.estimator import TfPoseEstimator
from tf_pose.networks import get_graph_path, model_wh

logger = logging.getLogger('TfPoseEstimatorRun')
logger.handlers.clear()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

TIMER = int(3)

#Initialize camera
cap = cv2.VideoCapture(0)

#Settings
w_cam = 432
h_cam = 368
resize_out_ratio = 4

#Return (index, coordinate_string, score)
def get_tuple_array(humans):
    ret_array = []
    human_string = str(humans[0])
    
    #print("Human", human_string)
    keypoints_list = human_string.split('BodyPart:')[1:]
    
    #'0-(0.52, 0.18) score=0.85 '
    print("List length", len(keypoints_list))
    for joint in keypoints_list:
        #['0-(0.52,', '0.18)', 'score=0.85', ''] we need to get rid of last one
        if len(joint.split(' ')) == '3':
            tuple = joint.split(' ')[:-1]
        else:
            tuple = joint.split(' ')
        index = float((tuple[0]+tuple[1]).split('-')[0])
        xy_coord = (tuple[0]+tuple[1]).split('-')[1]
        score = float(tuple[2].replace('score=',''))
        #print("index: ", index, " xy_coord: ", xy_coord, " score: ", score)
        ret_array.append((index, xy_coord, score))
    return ret_array
    
def compare_img_ret_accuracy(test_joint_array, ref_joint_array):
    
    #Now compare the joint coordinates
    #Loop through all joints
    #joint is a tuple of (index, coordinate_string, score)
    
    total = len(test_joint_array)
    correct = 0
    accuracy_arr = []
    
    if len(test_joint_array) != len(ref_joint_array):
        return -1
    for index in range(0,len(test_joint_array)):
        xy_threshold = 0.05
        
        test_joint = test_joint_array[index]
        x_coord_test = float(test_joint[1].split(',')[0].replace('(',''))
        y_coord_test = float(test_joint[1].split(',')[1].replace(')',''))
        
        ref_joint = ref_joint_array[index]
        x_coord_ref = float(ref_joint[1].split(',')[0].replace('(',''))
        y_coord_ref = float(ref_joint[1].split(',')[1].replace(')',''))
        
        if (x_coord_test >= x_coord_ref - xy_threshold and x_coord_test <= x_coord_ref + xy_threshold
            and y_coord_test >= y_coord_ref - xy_threshold and y_coord_test <= y_coord_ref + xy_threshold):
            correct+=1
            accuracy_arr.append((index, "Good"))
        else:
            accuracy_arr.append((index, "Bad"))

    accuracy = float(correct/total)
#    print("Correct: ", correct, "Accuracy", accuracy)
#    print(accuracy_arr)
    return accuracy

def print_good_job():
    pass

parser = argparse.ArgumentParser(description='tf-pose-estimation run')
parser.add_argument('--pose', type=str, default='warrior')
args = parser.parse_args()
pose = args.pose

#Get joints of skeleton from reference image
#pose = 'squat'
ref_image = cv2.imread('./images/references/' + pose + '_reference.jpg')
e = TfPoseEstimator(get_graph_path('mobilenet_thin'), target_size=(w_cam, h_cam))
humans_ref = e.inference(ref_image, resize_to_default=1, upsample_size=resize_out_ratio)
ref_joint_array = get_tuple_array(humans_ref)

#Save skeleton image with black background
black_background = np.zeros(ref_image.shape)
ref_skeleton_img = TfPoseEstimator.draw_humans(black_background, humans_ref, imgcopy=False)
filename_to_write = pose + '_reference_skeleton.jpg'
cv2.imwrite(filename_to_write, ref_skeleton_img)

#Create reference skeleton overlay using the black background
overlay = cv2.imread(pose + '_reference_skeleton.jpg')
overlayMask = cv2.cvtColor( overlay, cv2.COLOR_BGR2GRAY )
res, overlayMask = cv2.threshold( overlayMask, 10, 1, cv2.THRESH_BINARY_INV)

#Expand the mask from 1-channel to 3-channel
h,w = overlayMask.shape
overlayMask = np.repeat( overlayMask, 3).reshape( (h,w,3) )

timer_start = False

while True:
    
    ret, test_img = cap.read()
    test_img = cv2.flip(test_img,1)
    
    humans_test = e.inference(test_img, resize_to_default=(w > 0 and h > 0), upsample_size=resize_out_ratio)
    test_joint_array = []
    if len(humans_test) is not 0:
        test_joint_array = get_tuple_array(humans_test)
        test_img = TfPoseEstimator.draw_humans(test_img, humans_test, imgcopy=False)
    
    combined_image = test_img
    combined_image *= overlayMask
    combined_image += overlay

    k = cv2.waitKey(10)
    # Press q to break
    if k == ord('q'):
        break
    
    accuracy = compare_img_ret_accuracy(test_joint_array, ref_joint_array)
#str_accuracy = "{:.2f}".format(accuracy)
    str_accuracy = int(accuracy*100)
    status_arr = ["Get into position!", "Now hold for 3 secs!", "Great job!"]
    status = status_arr[0]
    font = cv2.FONT_HERSHEY_SIMPLEX
    acc_coord_from_top_left = (0,700) #bottom left corner
    #BGR
    yellow_color = (0, 255, 255)
    red_color = (0,0,255)
    green_color = (0,255,0)
    white_color = (255,255,255)
    color = yellow_color
    thickness = 4
    font_scale = 3

    timer_coord = (200,250)

    if accuracy >= 0.6:
        color = green_color
        status = status_arr[1]
        cv2.putText(combined_image, "GOOD: " + str(str_accuracy) + "%", acc_coord_from_top_left, font, font_scale, color, thickness, cv2.LINE_AA)
        #Start timer when it is false
        if timer_start is False:
            timer_start = True
            prev = time.time()
            cur = time.time()
        #Timer is already running
        else:
            cur = time.time()
        #If one second has elapsed
        if cur-prev >= 1:
            prev = cur
            TIMER = TIMER-1
        #If timer is up, break
        if TIMER <=0:
            status = status_arr[2]
            #Great job for 4 sec
            timeout = time.time() + 3   # 3 sec from now
            while timeout >= time.time():
                cv2.putText(combined_image, status, (0, 150), font, 2, yellow_color, thickness, cv2.LINE_AA)
                cv2.imshow('Hi', combined_image)
            break

    else:
        color = red_color
        status = status_arr[0]
        cv2.putText(combined_image, "BAD: " + str(str_accuracy), acc_coord_from_top_left, font, font_scale, color, thickness, cv2.LINE_AA)
        #reset timer back to 3 seconds
        TIMER = 3
        timer_start = False
    #Pose string
    cv2.putText(combined_image, pose.upper(), (0, 70), font, font_scale, yellow_color, thickness, cv2.LINE_AA, False) #top left corner
    #Timer string
    cv2.putText(combined_image, str(TIMER), timer_coord, font, font_scale, white_color, thickness, cv2.LINE_AA)
    #Status string
    cv2.putText(combined_image, status, (0, 150), font, 2, yellow_color, thickness, cv2.LINE_AA)
    cv2.imshow('Hi', combined_image)



# Release the camera and destroy all windows
cap.release()
cv2.destroyAllWindows()




