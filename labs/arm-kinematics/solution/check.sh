#!/usr/bin/env bash
# Автопроверка: DH-преобразование звена, прямая и обратная кинематика
# плоской 2-звенной руки. Чистый pytest, без rclpy/ROS2.
set -uo pipefail

FAIL=0
pass() { echo "  OK  $1"; }
fail() { echo "FAIL  $1"; FAIL=1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if ! python3 -c "import numpy" >/dev/null 2>&1; then
    echo "numpy не найден — установите: pip install numpy" >&2
    exit 1
fi
if ! command -v pytest >/dev/null 2>&1 && ! python3 -m pytest --version >/dev/null 2>&1; then
    echo "pytest не найден — установите: pip install pytest" >&2
    exit 1
fi

echo "=== Скрытые эталонные тесты (kinematics.py) ==="

REF_TEST="$(mktemp -d)/test_reference.py"
cat > "$REF_TEST" <<'PYEOF'
import sys
sys.path.insert(0, "HERE_PLACEHOLDER")
import numpy as np
import pytest
from kinematics import dh_transform, forward_kinematics, inverse_kinematics


def test_dh_transform_identity():
    T = dh_transform(0.0, 0.0, 0.0, 0.0)
    assert T == pytest.approx(np.eye(4), abs=1e-9)


def test_dh_transform_planar_link_example():
    # звено 1 плоской руки: theta1=30°, d=0, a1=1.0, alpha=0
    T = dh_transform(np.radians(30), 0.0, 1.0, 0.0)
    assert T[:3, 3] == pytest.approx([np.cos(np.radians(30)), np.sin(np.radians(30)), 0.0], abs=1e-9)
    assert T[3, :] == pytest.approx([0.0, 0.0, 0.0, 1.0], abs=1e-9)


def test_dh_transform_twisted_link():
    # alpha != 0 — звено со скруткой (вне плоского частного случая,
    # но dh_transform должна работать и для него)
    T = dh_transform(0.0, 1.0, 0.0, np.pi / 2)
    assert T[:3, 3] == pytest.approx([0.0, 0.0, 1.0], abs=1e-9)
    expected = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
    assert np.allclose(T[:3, :3], expected, atol=1e-9)


def test_forward_kinematics_two_link_example():
    dh_table = [
        (np.radians(30), 0.0, 1.0, 0.0),
        (np.radians(45), 0.0, 0.8, 0.0),
    ]
    T = forward_kinematics(dh_table)
    assert T[:2, 3] == pytest.approx([1.0730806398664554, 1.2727406610312546], abs=1e-6)
    angle = np.degrees(np.arctan2(T[1, 0], T[0, 0]))
    assert angle == pytest.approx(75.0, abs=1e-6)


def test_forward_kinematics_single_link_identity_angle():
    dh_table = [(0.0, 0.0, 1.0, 0.0)]
    T = forward_kinematics(dh_table)
    assert T[:3, 3] == pytest.approx([1.0, 0.0, 0.0], abs=1e-9)


def test_inverse_kinematics_elbow_up_roundtrip():
    a1, a2 = 1.0, 0.8
    x, y = 1.0730806398664554, 1.2727406610312546
    result = inverse_kinematics(x, y, a1, a2, elbow_up=True)
    assert result is not None
    theta1, theta2 = result
    assert theta1 == pytest.approx(np.radians(30), abs=1e-6)
    assert theta2 == pytest.approx(np.radians(45), abs=1e-6)


def test_inverse_kinematics_elbow_down_roundtrip():
    a1, a2 = 1.0, 0.8
    x, y = 1.0730806398664554, 1.2727406610312546
    result = inverse_kinematics(x, y, a1, a2, elbow_up=False)
    assert result is not None
    theta1, theta2 = result
    dh_table = [
        (theta1, 0.0, a1, 0.0),
        (theta2, 0.0, a2, 0.0),
    ]
    T = forward_kinematics(dh_table)
    assert T[:2, 3] == pytest.approx([x, y], abs=1e-6)
    assert theta2 < 0


def test_inverse_kinematics_out_of_reach():
    a1, a2 = 1.0, 0.8
    result = inverse_kinematics(10.0, 10.0, a1, a2, elbow_up=True)
    assert result is None
PYEOF
sed -i "s#HERE_PLACEHOLDER#$HERE#g" "$REF_TEST"

if python3 -m pytest "$REF_TEST" -v --no-header; then
    pass "все скрытые эталонные тесты прошли"
else
    fail "скрытые эталонные тесты не прошли (см. вывод выше)"
fi
rm -f "$REF_TEST"

echo "==="
if [ "$FAIL" -eq 0 ]; then
    echo "ИТОГ: зелёно."
else
    echo "ИТОГ: есть FAIL — см. выше."
fi
exit "$FAIL"
