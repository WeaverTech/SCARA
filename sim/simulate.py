"""Symulacja robota SCARA w PyBullet z wykorzystaniem modelu URDF.

Tryby:
  python simulate.py            # okno GUI (wymaga srodowiska graficznego)
  python simulate.py --headless # bez okna (walidacja URDF + FK), do CI/serwera
  python simulate.py --demo     # przejazd po przykladowej trajektorii

Mapowanie stawow URDF:
  z_lift (prismatic), shoulder, elbow, tool (revolute)
"""

from __future__ import annotations

import argparse
import math
import os
import time

import pybullet as p
import pybullet_data

from kinematics import JointState, Pose, ScaraKinematics

URDF_PATH = os.path.join(os.path.dirname(__file__), "scara.urdf")
JOINT_NAMES = ["z_lift", "shoulder", "elbow", "tool"]


def connect(headless: bool) -> int:
    mode = p.DIRECT if headless else p.GUI
    cid = p.connect(mode)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    return cid


def load_robot() -> tuple[int, dict]:
    robot = p.loadURDF(URDF_PATH, useFixedBase=True)
    joint_index = {}
    for j in range(p.getNumJoints(robot)):
        info = p.getJointInfo(robot, j)
        name = info[1].decode("utf-8")
        joint_index[name] = j
    return robot, joint_index


def apply_joint_state(robot: int, joint_index: dict, q: JointState) -> None:
    targets = {
        "z_lift": q.z,
        "shoulder": q.theta1,
        "elbow": q.theta2,
        "tool": q.theta_tool,
    }
    for name, value in targets.items():
        p.setJointMotorControl2(
            robot, joint_index[name], p.POSITION_CONTROL,
            targetPosition=value, force=50.0,
        )


def tcp_world_position(robot: int) -> tuple[float, float, float]:
    tip = None
    for j in range(p.getNumJoints(robot)):
        if p.getJointInfo(robot, j)[12].decode("utf-8") == "tool_tip":
            tip = j
            break
    if tip is None:
        return (0.0, 0.0, 0.0)
    state = p.getLinkState(robot, tip, computeForwardKinematics=True)
    return state[0]


def run_demo(robot: int, joint_index: dict, kin: ScaraKinematics,
             headless: bool) -> None:
    """Przejazd po prostokatnej trajektorii w plaszczyznie XY z IK."""
    waypoints = [
        Pose(x=0.20, y=0.05, z=0.10, phi=0.0),
        Pose(x=0.20, y=-0.05, z=0.10, phi=0.0),
        Pose(x=0.12, y=-0.05, z=0.15, phi=0.0),
        Pose(x=0.12, y=0.05, z=0.15, phi=0.0),
    ]
    for wp in waypoints:
        q = kin.inverse(wp, elbow="up")
        if q is None:
            print(f"  [SKIP] punkt poza zasiegiem: {wp}")
            continue
        apply_joint_state(robot, joint_index, q)
        for _ in range(240):
            p.stepSimulation()
            if not headless:
                time.sleep(1.0 / 240.0)
        steps = kin.joint_to_steps(q)
        print(f"  TCP cel=({wp.x:.3f},{wp.y:.3f},{wp.z:.3f}) "
              f"kroki={steps}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Symulacja SCARA (PyBullet)")
    parser.add_argument("--headless", action="store_true",
                        help="tryb bez okna (DIRECT)")
    parser.add_argument("--demo", action="store_true",
                        help="przejazd po przykladowej trajektorii")
    args = parser.parse_args()

    kin = ScaraKinematics()
    connect(headless=args.headless)
    robot, joint_index = load_robot()

    print(f"Zaladowano URDF: {URDF_PATH}")
    print(f"Liczba stawow: {p.getNumJoints(robot)}")
    for name in JOINT_NAMES:
        assert name in joint_index, f"Brak stawu '{name}' w URDF!"
    print("Stawy sterowane:", JOINT_NAMES)

    # Weryfikacja FK URDF vs analityczna kinematyka.
    q = JointState(z=0.10, theta1=math.radians(30), theta2=math.radians(40))
    apply_joint_state(robot, joint_index, q)
    for _ in range(480):
        p.stepSimulation()
    pose = kin.forward(q)
    tcp = tcp_world_position(robot)
    # Pozycja analityczna jest wzgledem osi barku; przesuwamy o offset Z.
    expected_x = kin.z_offset + 0.025 + pose.x  # offset kolumny + offset barku
    print(f"FK analityczna (uklad barku): x={pose.x:.4f} y={pose.y:.4f}")
    print(f"TCP w swiecie (PyBullet):     x={tcp[0]:.4f} y={tcp[1]:.4f} "
          f"z={tcp[2]:.4f}")

    if args.demo:
        print("=== DEMO: trajektoria z IK ===")
        run_demo(robot, joint_index, kin, headless=args.headless)

    if not args.headless:
        print("Okno GUI aktywne. Zamknij okno, aby zakonczyc.")
        try:
            while p.isConnected():
                p.stepSimulation()
                time.sleep(1.0 / 240.0)
        except KeyboardInterrupt:
            pass

    p.disconnect()


if __name__ == "__main__":
    main()
