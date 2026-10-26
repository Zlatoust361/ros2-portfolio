"""DH-преобразование звена, прямая и обратная кинематика плоской
2-звенной руки. Решение — см. README.md в родительской директории.
"""
import numpy as np


def dh_transform(theta, d, a, alpha):
    """Однородное преобразование 4x4 одного звена по таблице DH."""
    ct, st = np.cos(theta), np.sin(theta)
    ca, sa = np.cos(alpha), np.sin(alpha)
    return np.array([
        [ct, -st * ca,  st * sa, a * ct],
        [st,  ct * ca, -ct * sa, a * st],
        [0,          sa,      ca,      d],
        [0,           0,       0,      1],
    ])


def forward_kinematics(dh_table):
    """Прямая кинематика цепи произвольной длины."""
    T = np.eye(4)
    for theta, d, a, alpha in dh_table:
        T = T @ dh_transform(theta, d, a, alpha)
    return T


def inverse_kinematics(x, y, a1, a2, elbow_up=True):
    """Аналитическое IK для плоской 2-звенной цепи."""
    r2 = x * x + y * y
    cos_t2 = (r2 - a1 * a1 - a2 * a2) / (2 * a1 * a2)
    if abs(cos_t2) > 1.0:
        return None
    sin_t2 = np.sqrt(1.0 - cos_t2 ** 2)
    if not elbow_up:
        sin_t2 = -sin_t2
    theta2 = np.arctan2(sin_t2, cos_t2)
    k1 = a1 + a2 * cos_t2
    k2 = a2 * sin_t2
    theta1 = np.arctan2(y, x) - np.arctan2(k2, k1)
    return theta1, theta2
