float trans_cost(float gain)
{
	const float TRANS_LB = 0.86;
	const float TRANS_UB = 1.26;

	if (gain > TRANS_UB)
	{
		return std::pow(gain - TRANS_UB, 2);
	}
	else if (gain < TRANS_LB)
	{
		return std::pow(TRANS_LB - gain, 2);
	}
	else
	{
		return 0;
	}
}

float rotate_cost(float gain)
{
	const float ROTATE_LB = 0.67;
	const float ROTATE_UB = 1.24;

	if (gain > ROTATE_UB)
	{
		return std::pow(gain - ROTATE_UB, 2);
	}
	else if (gain < ROTATE_LB)
	{
		return std::pow(ROTATE_LB - gain, 2);
	}
	else
	{
		return 0;
	}
}

float intermediate_cost(float vir_steplength, float phy_steplength)
{
	const float RESET_COST = 5.0;

	float trans_gain = vir_steplength / phy_steplength;

	return RESET_COST + trans_cost(trans_gain) * vir_steplength;
}

float redirected_walking_cost(float vir_theta, float phy_theta, float vir_steplength, float vir_steptheta, float phy_steplength, float phy_steptheta)
{
	float RESET_COST = 5.0;

	float trans_gain = vir_steplength / phy_steplength;

	float cost_1 = RESET_COST + trans_cost(trans_gain) * vir_steplength;

	float vir_rotation = vir_steptheta - vir_theta;
	float phy_rotation = phy_steptheta - phy_theta;

	if (vir_rotation < 0)
	{
		vir_rotation += std::numbers::pi;
	}

	if (phy_rotation < 0)
	{
		phy_rotation += std::numbers::pi;
	}

	// clockwise rotation
	if (vir_rotation > std::numbers::pi / 2)
	{
		vir_rotation = std::numbers::pi - vir_rotation;
		phy_rotation = std::numbers::pi - phy_rotation;
	}

	float rotate_gain = vir_rotation / phy_rotation;
	float cost_2 = rotate_cost(rotate_gain) + trans_cost(trans_gain) * vir_steplength;

	return std::min(cost_1, cost_2);
}