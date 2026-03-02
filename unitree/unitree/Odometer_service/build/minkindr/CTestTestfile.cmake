# CMake generated Testfile for 
# Source directory: /home/unitree/unitree/Odometer_service/src/minkindr/minkindr
# Build directory: /home/unitree/unitree/Odometer_service/build/minkindr
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(_ctest_minkindr_gtest_minkindr_tests "/home/unitree/unitree/Odometer_service/build/minkindr/catkin_generated/env_cached.sh" "/usr/bin/python3" "/opt/ros/noetic/share/catkin/cmake/test/run_tests.py" "/home/unitree/unitree/Odometer_service/build/minkindr/test_results/minkindr/gtest-minkindr_tests.xml" "--return-code" "/home/unitree/unitree/Odometer_service/devel/.private/minkindr/lib/minkindr/minkindr_tests --gtest_output=xml:/home/unitree/unitree/Odometer_service/build/minkindr/test_results/minkindr/gtest-minkindr_tests.xml")
set_tests_properties(_ctest_minkindr_gtest_minkindr_tests PROPERTIES  _BACKTRACE_TRIPLES "/opt/ros/noetic/share/catkin/cmake/test/tests.cmake;160;add_test;/opt/ros/noetic/share/catkin/cmake/test/gtest.cmake;98;catkin_run_tests_target;/opt/ros/noetic/share/catkin/cmake/test/gtest.cmake;37;_catkin_add_google_test;/home/unitree/unitree/Odometer_service/src/minkindr/minkindr/CMakeLists.txt;9;catkin_add_gtest;/home/unitree/unitree/Odometer_service/src/minkindr/minkindr/CMakeLists.txt;0;")
subdirs("gtest")
