"""DH-преобразование звена, прямая и обратная кинематика плоской
2-звенной руки. Реализуйте три функции по TODO — спецификация в
докстрингах, подробности задачи в README.md.
"""
import numpy as np


def dh_transform(theta, d, a, alpha):
    """Однородное преобразование 4x4 одного звена по таблице DH.

    theta, d, a, alpha — параметры DH звена (theta, alpha в радианах).

    Возвращает numpy-массив формы (4, 4):
        [[cos(theta), -sin(theta)*cos(alpha),  sin(theta)*sin(alpha), a*cos(theta)],
         [sin(theta),  cos(theta)*cos(alpha), -cos(theta)*sin(alpha), a*sin(theta)],
         [         0,              sin(alpha),             cos(alpha),            d],
         [         0,                       0,                      0,            1]]
    """
    # TODO: реализовать по формуле выше
    raise NotImplementedError


def forward_kinematics(dh_table):
    """Прямая кинематика цепи произвольной длины.

    dh_table — список кортежей (theta, d, a, alpha), по одному на
    звено, от основания к схвату.

    Возвращает numpy-массив формы (4, 4) — T_base_to_tip, произведение
    dh_transform(...) всех звеньев по порядку (T1 @ T2 @ ... @ Tn).
    """
    # TODO: реализовать как произведение dh_transform(...) по порядку
    raise NotImplementedError


def inverse_kinematics(x, y, a1, a2, elbow_up=True):
    """Аналитическое IK для плоской 2-звенной цепи.

    x, y — целевое положение схвата; a1, a2 — длины звеньев;
    elbow_up — какую из двух ветвей решения вернуть
    (True -> sin(theta2) > 0, False -> sin(theta2) < 0).

    Возвращает кортеж (theta1, theta2) в радианах, либо None, если
    точка (x, y) вне рабочей зоны руки (|cos(theta2)| > 1).
    """
    # TODO: теорема косинусов -> cos(theta2); theta1 через atan2
    raise NotImplementedError
