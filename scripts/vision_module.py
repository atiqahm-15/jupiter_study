#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import math
import time

try:
    from ultralytics import YOLO
except ImportError:
    rospy.logwarn("Ultralytics YOLO not installed. Vision module will run in dummy mode.")
    YOLO = None

try:
    import mediapipe as mp
except ImportError:
    rospy.logwarn("MediaPipe not installed. Gesture recognition will be disabled.")
    mp = None

class VisionModule:
    def __init__(self, detection_callback):
        self.detection_callback = detection_callback
        self.bridge = CvBridge()
        
        # Load YOLO model for Person (0) and Cell Phone (67)
        if YOLO is not None:
            self.model = YOLO('yolov8n.pt') # Lightweight nano model
        else:
            self.model = None
            
        # MediaPipe for hand gesture detection and Face Mesh
        if mp is not None:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.hands = None
            self.face_mesh = None
            
        # Subscribe to camera image
        self.image_sub = rospy.Subscriber('/usb_cam/image_raw', Image, self.image_callback)
        
        # State tracking to avoid spamming
        self.person_present = False
        self.person_frames = 0
        self.missing_frames = 0
        self.phone_detected = False
        self.frames_since_last_phone = 0
        
        # Conversation tracking
        self.conversation_detected = False
        self.conversation_start_time = None
        self.last_talking_time = 0
        
        # Gesture tracking
        self.gesture_frames = 0
        self.current_gesture = None
        self.required_gesture_frames = 15 # Require ~15 consecutive frames for a gesture to register

    def calculate_distance(self, p1, p2):
        return math.hypot(p2.x - p1.x, p2.y - p1.y)

    def detect_gesture(self, hand_landmarks):
        """Simple heuristic for Thumbs Up and Open Palm."""
        # landmarks: 0 is wrist, 4 is thumb tip, 8 is index tip, 12 is middle tip, 16 is ring tip, 20 is pinky tip
        # mcp joints: 5, 9, 13, 17
        
        thumb_tip_y = hand_landmarks.landmark[4].y
        thumb_mcp_y = hand_landmarks.landmark[2].y
        
        index_tip_y = hand_landmarks.landmark[8].y
        index_mcp_y = hand_landmarks.landmark[5].y
        
        middle_tip_y = hand_landmarks.landmark[12].y
        middle_mcp_y = hand_landmarks.landmark[9].y
        
        ring_tip_y = hand_landmarks.landmark[16].y
        ring_mcp_y = hand_landmarks.landmark[13].y
        
        pinky_tip_y = hand_landmarks.landmark[20].y
        pinky_mcp_y = hand_landmarks.landmark[17].y
        
        # Check Peace Sign: Index and middle fingers extended, ring and pinky folded
        if (index_tip_y < index_mcp_y and middle_tip_y < middle_mcp_y and 
            ring_tip_y > ring_mcp_y and pinky_tip_y > pinky_mcp_y):
            return "PEACE_SIGN"
            
        # Check Thumbs Up: Thumb extended up (tip_y < mcp_y), other fingers folded (tip_y > mcp_y)
        if (thumb_tip_y < thumb_mcp_y and 
            index_tip_y > index_mcp_y and middle_tip_y > middle_mcp_y and 
            ring_tip_y > ring_mcp_y and pinky_tip_y > pinky_mcp_y):
            return "THUMBS_UP"
            
        return None

    def image_callback(self, data):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(e)
            return

        person_found = False
        phone_found = False

        # 1. Run YOLO for Person and Phone
        if self.model is not None:
            results = self.model(cv_image, verbose=False)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    if cls == 0 and conf > 0.5:
                        person_found = True
                    if cls == 67 and conf > 0.3:
                        phone_found = True

        # Process Person Presence
        if person_found:
            self.missing_frames = 0
            if not self.person_present:
                self.person_frames += 1
                if self.person_frames > 5:
                    self.person_present = True
                    self.detection_callback("PERSON_RETURNED")
        else:
            self.person_frames = 0
            if self.person_present:
                self.missing_frames += 1
                if self.missing_frames > 10:
                    self.person_present = False
                    self.detection_callback("PERSON_LEFT")
            
        # Process Phone Distraction
        if phone_found:
            self.frames_since_last_phone += 1
            if self.frames_since_last_phone > 10 and not self.phone_detected:
                self.phone_detected = True
                self.detection_callback("PHONE_DETECTED")
        else:
            self.frames_since_last_phone = 0
            self.phone_detected = False

        # 2. Run MediaPipe for Gestures and Face Mesh
        if self.hands is not None or self.face_mesh is not None:
            # MediaPipe expects RGB
            img_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            
        if self.face_mesh is not None:
            results_face = self.face_mesh.process(img_rgb)
            
            is_talking = False
            is_head_turned = False
            
            if results_face.multi_face_landmarks:
                for face_landmarks in results_face.multi_face_landmarks:
                    # Head pose heuristic: compare distance from nose to left/right eyes
                    nose = face_landmarks.landmark[1]
                    left_eye_outer = face_landmarks.landmark[33]
                    right_eye_outer = face_landmarks.landmark[263]
                    
                    dist_left = self.calculate_distance(nose, left_eye_outer)
                    dist_right = self.calculate_distance(nose, right_eye_outer)
                    
                    # If the ratio of distances is heavily skewed, head is turned
                    if dist_left > 1.5 * dist_right or dist_right > 1.5 * dist_left:
                        is_head_turned = True
                        
                    # Mouth Aspect Ratio (MAR)
                    top_lip = face_landmarks.landmark[13]
                    bottom_lip = face_landmarks.landmark[14]
                    left_lip = face_landmarks.landmark[78]
                    right_lip = face_landmarks.landmark[308]
                    
                    vertical_dist = self.calculate_distance(top_lip, bottom_lip)
                    horizontal_dist = self.calculate_distance(left_lip, right_lip)
                    
                    mar = vertical_dist / (horizontal_dist + 1e-6)
                    if mar > 0.05: # Threshold for mouth open (talking)
                        is_talking = True
                    break # Process only the first face
            
            if is_head_turned:
                if is_talking:
                    self.last_talking_time = time.time()
                    if self.conversation_start_time is None:
                        self.conversation_start_time = time.time()
                
                if self.conversation_start_time is not None:
                    if time.time() - self.last_talking_time > 1.0:
                        # Mouth hasn't moved in a while, reset
                        self.conversation_start_time = None
                        self.conversation_detected = False
                    elif time.time() - self.conversation_start_time > 3.0 and not self.conversation_detected:
                        self.conversation_detected = True
                        self.detection_callback("CONVERSATION_DETECTED")
            else:
                self.conversation_start_time = None
                self.conversation_detected = False
                
        if self.hands is not None:
            results_mp = self.hands.process(img_rgb)
            
            detected_gesture = None
            if results_mp.multi_hand_landmarks:
                for hand_landmarks in results_mp.multi_hand_landmarks:
                    detected_gesture = self.detect_gesture(hand_landmarks)
                    if detected_gesture:
                        break # Process only the first detected gesture
                        
            if detected_gesture:
                if detected_gesture == self.current_gesture:
                    self.gesture_frames += 1
                    if self.gesture_frames == self.required_gesture_frames:
                        if detected_gesture == "THUMBS_UP":
                            self.detection_callback("START_SESSION")
                        elif detected_gesture == "PEACE_SIGN":
                            self.detection_callback("STOP_SESSION")
                else:
                    self.current_gesture = detected_gesture
                    self.gesture_frames = 1
            else:
                self.current_gesture = None
                self.gesture_frames = 0
