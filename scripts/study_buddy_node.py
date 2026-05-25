#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Image
import sys
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from vision_module import VisionModule
from pomodoro_module import PomodoroModule
import time
from sound_play.libsoundplay import SoundClient


class StudyBuddyNode:
    def __init__(self):
        rospy.init_node('jupiter_study_buddy_node', anonymous=True)
        
        # Initialize sub-modules
        self.pomodoro = PomodoroModule(study_duration=25*60, break_duration=5*60)
        self.vision = VisionModule(detection_callback=self.vision_callback)
        
        self.pause_start_time = None
        self.max_pause_duration = 5 * 60 # 5 minutes
        self.leave_events = []
        self.last_conversation_warning_time = 0
        self.confirming_stop = False

        self.soundhandle = SoundClient()
        # Sleep briefly to ensure soundplay node is ready
        rospy.sleep(1)

        rospy.loginfo("Jupiter Study Buddy Initialized.")
        rospy.loginfo("Gesture 'Thumbs Up' to start/resume session.")
        rospy.loginfo("Gesture 'Peace Sign' to stop session.")

    def vision_callback(self, event):
        """Handle vision events (person left/returned, phone detected, gestures)"""
        # We might not want to log every single event if they happen frequently, but it's fine for now
        
        if event == "START_SESSION":
            if self.confirming_stop:
                self.confirming_stop = False
                msg = "Session paused."
                rospy.loginfo(f"Jupiter: {msg}")
                self.soundhandle.say(msg)
            else:
                if self.pomodoro.state == "IDLE" or self.pomodoro.state == "BREAK":
                    if self.pomodoro.start_session():
                        self.leave_events = []
                        msg = "Starting study session. Let's focus!"
                        rospy.loginfo(f"Jupiter: {msg}")
                        self.soundhandle.say(msg)
                elif self.pomodoro.state == "PAUSED":
                    if self.pomodoro.resume_session():
                        self.pause_start_time = None
                        msg = "Resuming session."
                        rospy.loginfo(f"Jupiter: {msg}")
                        self.soundhandle.say(msg)

        elif event == "STOP_SESSION":
            if self.confirming_stop:
                self.confirming_stop = False
                if self.pomodoro.stop_session():
                    self.pause_start_time = None
                    self.leave_events = []
                    msg = "Ending the session."
                    rospy.loginfo(f"Jupiter: {msg}")
                    self.soundhandle.say(msg)
            else:
                if self.pomodoro.state == "STUDYING" or self.pomodoro.state == "BREAK":
                    if self.pomodoro.pause_session():
                        self.pause_start_time = time.time()
                        self.confirming_stop = True
                        msg = "Do you want to end the session or just pause it? Show thumbs up to pause, or show the peace sign to end the session."
                        rospy.loginfo(f"Jupiter: {msg}")
                        self.soundhandle.say(msg)
                elif self.pomodoro.state == "PAUSED":
                    if self.pomodoro.stop_session():
                        self.pause_start_time = None
                        self.leave_events = []
                        msg = "Ending the session."
                        rospy.loginfo(f"Jupiter: {msg}")
                        self.soundhandle.say(msg)
        
        elif event == "PERSON_LEFT" and self.pomodoro.state == "STUDYING":
            current_time = time.time()
            self.leave_events.append(current_time)
            
            # Remove leave events older than 5 minutes
            self.leave_events = [t for t in self.leave_events if current_time - t <= 5 * 60]
            
            if len(self.leave_events) >= 3:
                msg = "You have left the session too many times. Automatically ending the session."
                rospy.loginfo(f"Jupiter: {msg}")
                self.soundhandle.say(msg)
                self.pomodoro.stop_session()
                self.pause_start_time = None
                self.leave_events = []
                self.confirming_stop = False
            else:
                self.pomodoro.pause_session()
                self.pause_start_time = current_time
                self.confirming_stop = False
                msg = "I see you left. Pausing the session."
                rospy.loginfo(f"Jupiter: {msg}")
                self.soundhandle.say(msg)
            
        elif event == "PERSON_RETURNED":
            self.confirming_stop = False
            if self.pomodoro.state == "PAUSED":
                msg = "Welcome back. Please show 'Thumbs Up' to resume the session."
                rospy.loginfo(f"Jupiter: {msg}")
                self.soundhandle.say(msg)
            elif self.pomodoro.state == "IDLE":
                msg = "Hi, welcome to the study session. Please show thumbs up to start session."
                rospy.loginfo(f"Jupiter: {msg}")
                self.soundhandle.say(msg)
            
        elif event == "CONVERSATION_DETECTED" and self.pomodoro.state == "STUDYING":
            current_time = time.time()
            if current_time - self.last_conversation_warning_time > 30: # 30 seconds cooldown
                msg = "I see someone else with you. Please try to minimize conversation and focus on your studies."
                rospy.loginfo(f"Jupiter: {msg}")
                self.soundhandle.say(msg)
                self.last_conversation_warning_time = current_time
 
        elif event == "PHONE_DETECTED" and self.pomodoro.state == "STUDYING":
            msg = "Please stay focused. Put the phone away."
            rospy.loginfo(f"Jupiter: {msg}")
            self.soundhandle.say(msg)

    def run(self):
        rate = rospy.Rate(1) # 1 Hz
        while not rospy.is_shutdown():
            # Check Pomodoro status
            status = self.pomodoro.check_status()
            
            if status == "BREAK_START":
                rospy.loginfo("Jupiter: Study session complete. Great job! Time for a short break.")
            elif status == "BREAK_END":
                rospy.loginfo("Jupiter: Break is over. Ready to start studying again? Show 'Thumbs Up'.")
                
            # Check 5-minute timeout if paused
            if self.pomodoro.state == "PAUSED" and self.pause_start_time is not None:
                if time.time() - self.pause_start_time > self.max_pause_duration:
                    rospy.loginfo("Jupiter: You have been away for 5 minutes. Automatically ending the session.")
                    self.pomodoro.stop_session()
                    self.pause_start_time = None
                    self.leave_events = []
                    self.confirming_stop = False
                    
            # Display live timer in terminal
            if self.pomodoro.state in ["STUDYING", "BREAK", "PAUSED"]:
                mins, secs = self.pomodoro.get_time_remaining()
                sys.stdout.write(f"\r[{self.pomodoro.state}] Time remaining: {mins:02d}:{secs:02d}   ")
                sys.stdout.flush()
            elif self.pomodoro.state == "IDLE":
                sys.stdout.write(f"\r[IDLE] Waiting for session to start...               ")
                sys.stdout.flush()
                
            rate.sleep()

if __name__ == '__main__':
    try:
        node = StudyBuddyNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
