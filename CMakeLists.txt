cmake_minimum_required(VERSION 3.0.2)
project(jupiter_study)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
  geometry_msgs
  cv_bridge
  sound_play
)

catkin_package()


catkin_install_python(PROGRAMS
  scripts/study_buddy_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
