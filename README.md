# Jupiter Study Buddy

An autonomous, camera-based study companion node for ROS 1. Jupiter helps you maintain focus during study sessions using Pomodoro timers, distraction detection, gesture-based controls, and text-to-speech audio feedback.

Jupiter relies entirely on computer vision and deep learning models to monitor your study space, track your focus levels, and respond to hand gestures.

---

## Key Features

- ⏱️ **Integrated Pomodoro Timer**: Built-in state machine managing standard 25-minute study intervals followed by 5-minute breaks.
- ✌️ **Gesture Control**: Use hand gestures to start, pause, and stop/terminate your study session.
- 📱 **Distraction Detection**: Automatically detects if you are using your phone and verbally warns you to put it away.
- 🚶 **Smart Presence Tracking**: Pauses the session automatically if you leave the camera's view. If you stay away for more than 5 minutes, it ends the session.
- 🗣️ **Conversational Warnings**: Warns you to minimize conversation if you are talking to someone else in the room during study sessions.
- 📢 **Audio Feedback & Notifications**: Speaks reminders, alerts, and instructions via standard ROS speech synthesis.

---

## Project Structure

The project is structured as a standard ROS 1 package with modular Python scripts:

* 📁 **[launch](file:///c:/Users/User/Documents/jupiter_study/launch)**: Contains ROS launch configurations.
  * [jupiter.launch](file:///c:/Users/User/Documents/jupiter_study/launch/jupiter.launch): Launch file starting `soundplay_node` and `study_buddy_node`.
* 📁 **[scripts](file:///c:/Users/User/Documents/jupiter_study/scripts)**: Core Python logic.
  * [study_buddy_node.py](file:///c:/Users/User/Documents/jupiter_study/scripts/study_buddy_node.py) ([StudyBuddyNode](file:///c:/Users/User/Documents/jupiter_study/scripts/study_buddy_node.py#L18)): The central orchestrator that coordinates vision events, the timer, and voice notifications.
  * [vision_module.py](file:///c:/Users/User/Documents/jupiter_study/scripts/vision_module.py) ([VisionModule](file:///c:/Users/User/Documents/jupiter_study/scripts/vision_module.py#L22)): Manages the OpenCV, MediaPipe, and YOLOv8 models for detecting gestures, faces, presence, and distractions.
  * [pomodoro_module.py](file:///c:/Users/User/Documents/jupiter_study/scripts/pomodoro_module.py) ([PomodoroModule](file:///c:/Users/User/Documents/jupiter_study/scripts/pomodoro_module.py#L7)): Houses the state machine logic for managing study, break, pause, and idle states.
* [CMakeLists.txt](file:///c:/Users/User/Documents/jupiter_study/CMakeLists.txt) & [package.xml](file:///c:/Users/User/Documents/jupiter_study/package.xml): ROS package metadata and dependencies.

---

## Dependencies

This package requires ROS 1 (e.g., Noetic) and a few Python libraries. Make sure you install the Python dependencies using `pip`:

```bash
# Core vision and bridge libraries
pip install opencv-python cv-bridge

# For hand gesture and face landmark tracking
pip install mediapipe

# For object detection (Person and Phone)
pip install ultralytics
```

System dependencies:
```bash
sudo apt-get install ros-noetic-sound-play
```

---

## Setup & Running

1. **Start your camera node**: Jupiter needs an active image stream to process. By default, it subscribes to `/usb_cam/image_raw`. You can publish your webcam feed using standard camera nodes:
   ```bash
   roscore
   rosrun usb_cam usb_cam_node
   ```

2. **Make the scripts executable**:
   ```bash
   cd c:/Users/User/Documents/jupiter_study/scripts
   chmod +x study_buddy_node.py vision_module.py pomodoro_module.py
   ```
   *(Note: Adjust paths if you are running on Windows vs WSL/Linux)*

3. **Run the Jupiter Node**:
   Run the launch file which starts the speech synthesis engine and the study buddy node:
   ```bash
   # From your ROS workspace, assuming you have sourced devel/setup.bash
   roslaunch jupiter_study jupiter.launch
   ```
   *Note: On the first run, YOLOv8 will automatically download the lightweight `yolov8n.pt` model weights.*

---

## How to Use

Everything is communicated via standard ROS terminal logs (`rospy.loginfo`) and spoken voice alerts. Keep your speakers turned on and watch the terminal output!

### Gestures
Hold the gesture clearly in front of the camera for about 1 second (~15 frames) to register:
* 👍 **Thumbs Up**: Starts a new study session, resumes a paused session, or confirms pausing.
* ✌️ **Peace Sign**: Pauses the current session and initiates the stop confirmation prompt. Show the Peace Sign twice to stop the session completely.

### Automated Behaviors
* **Absence / Leaving**: 
  - If you leave the camera's field of view while studying, Jupiter automatically **pauses** the session.
  - If you return, Jupiter greets you and asks you to show a **Thumbs Up** to resume.
  - **Absence Timeout**: If you stay away for more than **5 minutes** while paused, Jupiter automatically ends the session.
  - **Frequent Breaks Limit**: If you leave the session more than **3 times within a rolling 5-minute window**, Jupiter terminates the session.
* **Distractions**: If Jupiter spots a cell phone (`class 67`) in the frame, it verbally warns you: *"Please stay focused. Put the phone away."*
* **Conversations**: If Jupiter detects that your head is turned and you are talking (open mouth) for more than 3 seconds, it warns you: *"I see someone else with you. Please try to minimize conversation and focus on your studies."*
