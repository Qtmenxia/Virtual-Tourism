#!/bin/sh

if [ -n "$DESTDIR" ] ; then
    case $DESTDIR in
        /*) # ok
            ;;
        *)
            /bin/echo "DESTDIR argument must be absolute... "
            /bin/echo "otherwise python's distutils will bork things."
            exit 1
    esac
fi

echo_and_run() { echo "+ $@" ; "$@" ; }

echo_and_run cd "/home/unitree/unitree/Odometer_service/src/rpg_svo_pro_open/rqt_svo"

# ensure that Python install destination exists
echo_and_run mkdir -p "$DESTDIR/home/unitree/unitree/Odometer_service/install/lib/python3/dist-packages"

# Note that PYTHONPATH is pulled from the environment to support installing
# into one location when some dependencies were installed in another
# location, #123.
echo_and_run /usr/bin/env \
    PYTHONPATH="/home/unitree/unitree/Odometer_service/install/lib/python3/dist-packages:/home/unitree/unitree/Odometer_service/build/rqt_svo/lib/python3/dist-packages:$PYTHONPATH" \
    CATKIN_BINARY_DIR="/home/unitree/unitree/Odometer_service/build/rqt_svo" \
    "/usr/bin/python3" \
    "/home/unitree/unitree/Odometer_service/src/rpg_svo_pro_open/rqt_svo/setup.py" \
     \
    build --build-base "/home/unitree/unitree/Odometer_service/build/rqt_svo" \
    install \
    --root="${DESTDIR-/}" \
    --install-layout=deb --prefix="/home/unitree/unitree/Odometer_service/install" --install-scripts="/home/unitree/unitree/Odometer_service/install/bin"
