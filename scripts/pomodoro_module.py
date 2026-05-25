#!/usr/bin/env python3

import rospy
import time
from std_msgs.msg import String

class PomodoroModule:
    def __init__(self, study_duration=25*60, break_duration=5*60):
        self.study_duration = study_duration
        self.break_duration = break_duration
        self.state = "IDLE" # IDLE, STUDYING, PAUSED, BREAK
        self.start_time = 0
        self.paused_time = 0
        self.elapsed_time = 0

    def start_session(self):
        if self.state == "IDLE" or self.state == "BREAK":
            self.state = "STUDYING"
            self.start_time = time.time()
            self.elapsed_time = 0
            rospy.loginfo("Pomodoro: Started study session.")
            return True
        return False

    def pause_session(self):
        if self.state == "STUDYING":
            self.state = "PAUSED"
            self.elapsed_time += time.time() - self.start_time
            rospy.loginfo("Pomodoro: Paused study session.")
            return True
        return False

    def resume_session(self):
        if self.state == "PAUSED":
            self.state = "STUDYING"
            self.start_time = time.time()
            rospy.loginfo("Pomodoro: Resumed study session.")
            return True
        return False

    def stop_session(self):
        self.state = "IDLE"
        self.elapsed_time = 0
        rospy.loginfo("Pomodoro: Stopped session.")
        return True

    def check_status(self):
        if self.state == "STUDYING":
            current_elapsed = self.elapsed_time + (time.time() - self.start_time)
            if current_elapsed >= self.study_duration:
                self.state = "BREAK"
                self.start_time = time.time()
                self.elapsed_time = 0
                rospy.loginfo("Pomodoro: Study session complete. Starting break.")
                return "BREAK_START"
        elif self.state == "BREAK":
            current_elapsed = time.time() - self.start_time
            if current_elapsed >= self.break_duration:
                self.state = "IDLE"
                rospy.loginfo("Pomodoro: Break complete.")
                return "BREAK_END"
        return self.state

    def get_time_remaining(self):
        if self.state == "STUDYING":
            current_elapsed = self.elapsed_time + (time.time() - self.start_time)
            remaining = max(0, self.study_duration - current_elapsed)
            return int(remaining // 60), int(remaining % 60)
        elif self.state == "BREAK":
            current_elapsed = time.time() - self.start_time
            remaining = max(0, self.break_duration - current_elapsed)
            return int(remaining // 60), int(remaining % 60)
        elif self.state == "PAUSED":
            remaining = max(0, self.study_duration - self.elapsed_time)
            return int(remaining // 60), int(remaining % 60)
        return 0, 0
