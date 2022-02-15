from math import pi

def trans_cost(gain: float) -> float:
	if (gain > 1.26):
		return pow(gain - 0.86, 2)
	elif (gain < 0.86):
		return pow(0.86 - gain, 2)
	else:
	    return 0

def rotate_cost(gain: float) -> float:
	if (gain > 1.24):
		return pow(gain - 1.24, 2)
	elif (gain < 0.67):
		return pow(0.67 - gain, 2)
	else:
		return 0
    
def intermediate_cost(vir_steplength: float, phy_steplength: float) -> float:
	return 5.0 + trans_cost(vir_steplength / phy_steplength) * vir_steplength

"""

"""
def redirected_walking_cost(vir_theta: float, phy_theta: float, vir_steplength: float, vir_steptheta: float, phy_steplength: float, phy_steptheta: float) -> float:
	cost_1 = 5.0 + trans_cost(vir_steplength / phy_steplength) * vir_steplength
	vir_rotation = vir_steptheta - vir_theta
	phy_rotation = phy_steptheta - phy_theta

	if (vir_rotation < 0):
		vir_rotation += pi

	if (phy_rotation < 0):
		phy_rotation += pi

	# clockwise rotation
	if (vir_rotation > pi / 2):
		vir_rotation = pi - vir_rotation
		phy_rotation = pi - phy_rotation

	cost_2 = rotate_cost(vir_rotation / phy_rotation) + trans_cost(vir_steplength / phy_steplength) * vir_steplength

	return min(cost_1, cost_2)