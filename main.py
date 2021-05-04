from scipy.spatial import distance as dist
from imutils import face_utils
from threading import Thread
import numpy as np
import dlib
import cv2
import pyfirmata
 
pin= 2                           #relay connect to pin 2 Arduino
port = 'COM7'                    #select port COM, check device manager
board = pyfirmata.Arduino(port)



def eye_aspect_ratio(eye):
	# compute the euclidean distances between the two sets of
	# vertical eye landmarks (x, y)-coordinates
	A = dist.euclidean(eye[1], eye[5])
	B = dist.euclidean(eye[2], eye[4])

	# compute the euclidean distance between the horizontal
	# eye landmark (x, y)-coordinates
	C = dist.euclidean(eye[0], eye[3])

	# compute the eye aspect ratio
	ear = (A + B) / (2.0 * C)

	# return the eye aspect ratio
	return ear

def mouth_aspect_ratio(mouth):
	
	A = dist.euclidean(mouth[13], mouth[19])
	B = dist.euclidean(mouth[14], mouth[18])
	C = dist.euclidean(mouth[15], mouth[17])

	# compute the mouth aspect ratio
	mar = (A+B+C)/3.0

	# return the eye aspect ratio
	return mar

# define two constants, one for the eye aspect ratio to indicate
# blink and then a second constant for the number of consecutive
# frames the eye must be below the threshold for to set off the
# alarm
EYE_AR_THRESH = 0.25
MOUTH_AR_THRESH = 35
EYE_AR_CONSEC_FRAMES = 10

# initialize the frame counter as well as a boolean used to
# indicate if the alarm is going off
COUNTER = 0
ALARM_ON = False

# initialize dlib's face detector (HOG-based) and then create
# the facial landmark predictor
print("[INFO] loading facial landmark predictor...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# grab the indexes of the facial landmarks for the left and
# right eye, respectively
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
(mStart, mEnd) = face_utils.FACIAL_LANDMARKS_IDXS["mouth"]

# start the video stream thread
print("[INFO] starting video stream thread...")

vs = cv2.VideoCapture(0)
vs.set(3, 1280)
vs.set(4, 720)


# loop over frames from the video stream
while True:
	# grab the frame from the threaded video file stream, resize
	# it, and convert it to grayscale
	# channels)
	_, frame = vs.read()
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

	# detect faces in the grayscale frame
	rects = detector(gray, 0)

# loop over the face detections
	for rect in rects:
		# determine the facial landmarks for the face region, then
		# convert the facial landmark (x, y)-coordinates to a NumPy
		# array
		shapes = predictor(gray, rect)
		shape = face_utils.shape_to_np(shapes)

		# extract the left and right eye coordinates, then use the
		# coordinates to compute the eye aspect ratio for both eyes
		mouth    = shape[mStart:mEnd]
		leftEye  = shape[lStart:lEnd]
		rightEye = shape[rStart:rEnd]
		mar      = mouth_aspect_ratio(mouth)
		leftEAR  = eye_aspect_ratio(leftEye)
		rightEAR = eye_aspect_ratio(rightEye)

		# average the eye aspect ratio together for both eyes
		ear = (leftEAR + rightEAR) / 2.0
		

		# compute the convex hull for the left and right eye, then
		# visualize each of the eyes
		mouthHull    = cv2.convexHull(mouth)
		leftEyeHull  = cv2.convexHull(leftEye)
		rightEyeHull = cv2.convexHull(rightEye)
		cv2.drawContours(frame, [mouthHull], -1, (0, 255, 0), 1)
		cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
		cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

	

		# check to see if the eye aspect ratio is below the blink
		# threshold, and if so, increment the blink frame counter
		if mar > MOUTH_AR_THRESH or ear < EYE_AR_THRESH :
			COUNTER += 1

			# if the eyes were closed for a sufficient number of
			# then sound the alarm
			if COUNTER >= EYE_AR_CONSEC_FRAMES:
				# draw an alarm on the frame
				cv2.rectangle(frame, (10, 17), (690, 100), (0, 0, 255), cv2.FILLED)
				cv2.putText(frame, "DROWSINESS ALERT!!!", (10, 70),
				cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
				board.digital[pin].write(0)

		# otherwise, the eye aspect ratio is not below the blink
		# threshold, so reset the counter and alarm
		else:
			COUNTER = 0
			board.digital[pin].write(1)

        # draw the computed eye aspect ratio on the frame to help
		# with debugging and setting the correct eye aspect ratio
		# thresholds and frame counters

	
	cv2.putText(frame, "EAR: {:.2f}".format(ear), (900, 70),
	cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
	cv2.putText(frame, "MAR: {:.2f}".format(mar), (900, 110),
	cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
 
 
	# show the frame
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF
 
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break
# do a bit of cleanup
cv2.destroyAllWindows()