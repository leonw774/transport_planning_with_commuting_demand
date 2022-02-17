#include <math.h>
#define PI 3.141592653

double trans_cost(double gain)
{
	const double TRANS_LB = 0.86;
	const double TRANS_UB = 1.26;

	if (gain > TRANS_UB)
	{
		return pow(gain - TRANS_UB, 2);
	}
	else if (gain < TRANS_LB)
	{
		return pow(TRANS_LB - gain, 2);
	}
	else
	{
		return 0;
	}
}

double rotate_cost(double gain)
{
	const double ROTATE_LB = 0.67;
	const double ROTATE_UB = 1.24;

	if (gain > ROTATE_UB)
	{
		return pow(gain - ROTATE_UB, 2);
	}
	else if (gain < ROTATE_LB)
	{
		return pow(ROTATE_LB - gain, 2);
	}
	else
	{
		return 0;
	}
}

double redirected_walking_cost(double vir_theta, double phy_theta, double vir_steplength, double vir_steptheta, double phy_steplength, double phy_steptheta)
{
	double RESET_COST = 5.0;

	double trans_gain = vir_steplength / phy_steplength;

	double cost_1 = RESET_COST + trans_cost(trans_gain) * vir_steplength;

	double vir_rotation = vir_steptheta - vir_theta;
	double phy_rotation = phy_steptheta - phy_theta;

	if (vir_rotation < 0)
	{
		vir_rotation += PI;
	}

	if (phy_rotation < 0)
	{
		phy_rotation += PI;
	}

	// clockwise rotation
	if (vir_rotation > PI / 2)
	{
		vir_rotation = PI - vir_rotation;
		phy_rotation = PI - phy_rotation;
	}

	double rotate_gain = vir_rotation / phy_rotation;
	double cost_2 = rotate_cost(rotate_gain) + trans_cost(trans_gain) * vir_steplength;

	return (cost_1 < cost_2) ? cost_1 : cost_2;
}