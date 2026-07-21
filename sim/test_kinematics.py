"""Testy kinematyki SCARA: round-trip FK/IK, limity, mapowanie krokow."""

import math

import pytest

from kinematics import (
    J1_STEPS_PER_DEG,
    J2_STEPS_PER_DEG,
    Z_STEPS_PER_MM,
    JointState,
    Pose,
    ScaraKinematics,
)


@pytest.fixture
def kin() -> ScaraKinematics:
    return ScaraKinematics()


def test_constants_match_firmware():
    # (200 * 16 * 20) / 360 = 177.7778 (bark, cykloidalna 20:1)
    assert J1_STEPS_PER_DEG == pytest.approx(177.7778, abs=1e-3)
    # (200 * 16 * 14) / 360 = 124.4444 (lokiec, cykloidalna 14:1)
    assert J2_STEPS_PER_DEG == pytest.approx(124.4444, abs=1e-3)
    # Sruba napedowa osi Z.
    assert Z_STEPS_PER_MM == pytest.approx(400.0, abs=1e-6)


def test_geometry_matches_cad():
    kin = ScaraKinematics()
    assert kin.l1 == pytest.approx(0.139928, abs=1e-9)
    assert kin.l2 == pytest.approx(0.140000, abs=1e-9)
    # MAX_REACH = L1 + L2 = 279.928 mm, MIN_REACH = |L1 - L2| = 0.072 mm
    assert (kin.l1 + kin.l2) * 1000.0 == pytest.approx(279.928, abs=1e-6)
    assert abs(kin.l1 - kin.l2) * 1000.0 == pytest.approx(0.072, abs=1e-6)


def test_column_exclusion_zone():
    kin = ScaraKinematics()
    # Punkt w srodku kolumny (x = -z_offset) - zabroniony.
    assert kin.in_column_exclusion(-kin.z_offset, 0.0)
    # Punkt 44 mm od osi kolumny - nadal w strefie (promien 45 mm).
    assert kin.in_column_exclusion(-kin.z_offset + 0.044, 0.0)
    # Punkt 46 mm od osi kolumny - poza strefa.
    assert not kin.in_column_exclusion(-kin.z_offset + 0.046, 0.0)
    # Typowy punkt roboczy przed robotem - poza strefa.
    assert not kin.in_column_exclusion(0.200, 0.050)


@pytest.mark.parametrize(
    "t1_deg,t2_deg,tool_deg,z",
    [
        (30, 45, 0, 0.10),
        (0, 90, 15, 0.0),
        (-45, -60, -30, 0.20),
        (120, -90, 45, 0.05),
        (10, 5, 0, 0.30),
    ],
)
def test_fk_ik_roundtrip(kin, t1_deg, t2_deg, tool_deg, z):
    q = JointState(
        z=z,
        theta1=math.radians(t1_deg),
        theta2=math.radians(t2_deg),
        theta_tool=math.radians(tool_deg),
    )
    pose = kin.forward(q)
    elbow = "up" if t2_deg >= 0 else "down"
    q_back = kin.inverse(pose, elbow=elbow)
    assert q_back is not None

    pose_back = kin.forward(q_back)
    assert pose_back.x == pytest.approx(pose.x, abs=1e-6)
    assert pose_back.y == pytest.approx(pose.y, abs=1e-6)
    assert pose_back.z == pytest.approx(pose.z, abs=1e-9)
    # Orientacja narzedzia (z dokladnoscia do 2*pi).
    dphi = math.atan2(
        math.sin(pose_back.phi - pose.phi), math.cos(pose_back.phi - pose.phi)
    )
    assert dphi == pytest.approx(0.0, abs=1e-6)


def test_out_of_reach_returns_none(kin):
    pose = Pose(x=kin.l1 + kin.l2 + 0.05, y=0.0, z=0.1, phi=0.0)
    assert kin.inverse(pose) is None


def test_inner_limit_out_of_reach():
    kin = ScaraKinematics(l1=0.150, l2=0.100)
    # Punkt blizej niz |L1 - L2| = 0.05 m.
    pose = Pose(x=0.01, y=0.0, z=0.1, phi=0.0)
    assert kin.inverse(pose) is None


def test_elbow_up_down_differ(kin):
    pose = Pose(x=0.15, y=0.10, z=0.1, phi=0.0)
    up = kin.inverse(pose, elbow="up")
    down = kin.inverse(pose, elbow="down")
    assert up is not None and down is not None
    assert up.theta2 * down.theta2 <= 0  # przeciwne znaki
    # Obie konfiguracje musza dawac ten sam TCP.
    for q in (up, down):
        pb = kin.forward(q)
        assert pb.x == pytest.approx(pose.x, abs=1e-6)
        assert pb.y == pytest.approx(pose.y, abs=1e-6)


def test_step_mapping(kin):
    q = JointState(z=0.010, theta1=math.radians(1.0),
                   theta2=math.radians(1.0), theta_tool=0.0)
    steps = kin.joint_to_steps(q)
    assert steps["z"] == round(10.0 * Z_STEPS_PER_MM)  # 10 mm
    assert steps["shoulder"] == round(J1_STEPS_PER_DEG)  # 1 deg (20:1)
    assert steps["elbow"] == round(J2_STEPS_PER_DEG)  # 1 deg (14:1)


def test_within_limits(kin):
    ok = JointState(z=0.1, theta1=0.0, theta2=0.0, theta_tool=0.0)
    assert kin.within_limits(ok)
    too_high = JointState(z=0.5, theta1=0.0, theta2=0.0, theta_tool=0.0)
    assert not kin.within_limits(too_high)
