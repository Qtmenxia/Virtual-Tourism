# Install script for directory: /home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/home/unitree/unitree/Odometer_service/devel/.private/ceres_catkin")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ceres" TYPE FILE FILES
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/autodiff_cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/autodiff_local_parameterization.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/c_api.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/ceres.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/conditioned_cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/context.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/cost_function_to_functor.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/covariance.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/crs_matrix.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/cubic_interpolation.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/dynamic_autodiff_cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/dynamic_cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/dynamic_cost_function_to_functor.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/dynamic_numeric_diff_cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/evaluation_callback.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/fpclassify.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/gradient_checker.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/gradient_problem.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/gradient_problem_solver.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/iteration_callback.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/jet.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/local_parameterization.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/loss_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/normal_prior.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/numeric_diff_cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/numeric_diff_options.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/ordered_groups.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/problem.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/rotation.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/sized_cost_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/solver.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/tiny_solver.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/tiny_solver_autodiff_function.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/tiny_solver_cost_function_adapter.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/types.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/version.h"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ceres/internal" TYPE FILE FILES
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/autodiff.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/disable_warnings.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/eigen.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/fixed_array.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/macros.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/manual_constructor.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/numeric_diff.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/port.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/reenable_warnings.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/scoped_ptr.h"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/include/ceres/internal/variadic_evaluate.h"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ceres/internal" TYPE FILE FILES "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/config/ceres/internal/config.h")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres/CeresTargets.cmake")
    file(DIFFERENT EXPORT_FILE_CHANGED FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres/CeresTargets.cmake"
         "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/CMakeFiles/Export/lib/cmake/Ceres/CeresTargets.cmake")
    if(EXPORT_FILE_CHANGED)
      file(GLOB OLD_CONFIG_FILES "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres/CeresTargets-*.cmake")
      if(OLD_CONFIG_FILES)
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres/CeresTargets.cmake\" will be replaced.  Removing files [${OLD_CONFIG_FILES}].")
        file(REMOVE ${OLD_CONFIG_FILES})
      endif()
    endif()
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres" TYPE FILE FILES "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/CMakeFiles/Export/lib/cmake/Ceres/CeresTargets.cmake")
  if("${CMAKE_INSTALL_CONFIG_NAME}" MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres" TYPE FILE FILES "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/CMakeFiles/Export/lib/cmake/Ceres/CeresTargets-release.cmake")
  endif()
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres" TYPE FILE RENAME "CeresConfig.cmake" FILES "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/CeresConfig-install.cmake")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/Ceres" TYPE FILE FILES
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/CeresConfigVersion.cmake"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/cmake/FindEigen.cmake"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/cmake/FindGlog.cmake"
    "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src/cmake/FindGflags.cmake"
    )
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/internal/ceres/cmake_install.cmake")

endif()

if(CMAKE_INSTALL_COMPONENT)
  set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
file(WRITE "/home/unitree/unitree/Odometer_service/build/ceres_catkin/ceres_src-prefix/src/ceres_src-build/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
